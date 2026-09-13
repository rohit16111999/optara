"""A bounded interpreter for a deliberately tiny Python AST subset.

No exec/eval, imports, object traversal, files, network, reflection or recursion.
Unsupported programs receive an explicit evaluator limitation, never host execution.
"""
import ast
import operator


class UnsupportedCode(ValueError): pass
class Returned(Exception):
    def __init__(self,value): self.value=value


class Interpreter:
    BIN={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
    CMP={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.In:lambda a,b:a in b,ast.NotIn:lambda a,b:a not in b,ast.Is:operator.is_,ast.IsNot:operator.is_not}
    BUILTINS={'set':set,'list':list,'tuple':tuple,'len':len,'max':max,'min':min,'sum':sum,'abs':abs,'sorted':sorted,'range':range,'enumerate':enumerate,'isinstance':isinstance,'int':int,'float':float,'str':str,'bool':bool}

    def __init__(self): self.steps=0

    def tick(self):
        self.steps+=1
        if self.steps>20000: raise UnsupportedCode('20,000-step evaluation limit reached')

    def bounded(self,value):
        if isinstance(value,(list,tuple,set,dict,str,range)) and len(value)>10000: raise UnsupportedCode('Collection size limit reached')
        if isinstance(value,int) and value.bit_length()>256: raise UnsupportedCode('Integer size limit reached')
        return value

    def expression(self,node,env):
        self.tick()
        if isinstance(node,ast.Constant): return self.bounded(node.value)
        if isinstance(node,ast.Name):
            if node.id in {'int','float','str','bool','list','tuple','set'}: return self.BUILTINS[node.id]
            if node.id not in env: raise UnsupportedCode('Undefined or forbidden name: '+node.id)
            return env[node.id]
        if isinstance(node,(ast.List,ast.Tuple,ast.Set)):
            ctor={ast.List:list,ast.Tuple:tuple,ast.Set:set}[type(node)]
            return self.bounded(ctor(self.expression(v,env) for v in node.elts))
        if isinstance(node,ast.Dict): return {self.expression(k,env):self.expression(v,env) for k,v in zip(node.keys,node.values)}
        if isinstance(node,(ast.ListComp,ast.SetComp,ast.GeneratorExp)):
            values=[]
            def collect(index,local):
                self.tick()
                if index==len(node.generators):
                    values.append(self.expression(node.elt,local));self.bounded(values);return
                generator=node.generators[index]
                if generator.is_async: raise UnsupportedCode('Async comprehension is not supported')
                for value in self.expression(generator.iter,local):
                    self.tick();child=dict(local);self.assign(generator.target,value,child)
                    if all(self.expression(check,child) for check in generator.ifs): collect(index+1,child)
            collect(0,dict(env))
            return set(values) if isinstance(node,ast.SetComp) else values
        if isinstance(node,ast.BinOp) and type(node.op) in self.BIN:
            left,right=self.expression(node.left,env),self.expression(node.right,env)
            if isinstance(node.op,ast.Mult) and ((isinstance(left,(str,list,tuple)) and isinstance(right,int) and len(left)*abs(right)>10000) or (isinstance(right,(str,list,tuple)) and isinstance(left,int) and len(right)*abs(left)>10000)):
                raise UnsupportedCode('Allocation limit reached')
            return self.bounded(self.BIN[type(node.op)](left,right))
        if isinstance(node,ast.UnaryOp):
            value=self.expression(node.operand,env)
            if isinstance(node.op,ast.Not): return not value
            if isinstance(node.op,ast.USub): return -value
            if isinstance(node.op,ast.UAdd): return value
        if isinstance(node,ast.BoolOp):
            for item in node.values:
                value=self.expression(item,env)
                if isinstance(node.op,ast.And) and not value: return value
                if isinstance(node.op,ast.Or) and value: return value
            return value
        if isinstance(node,ast.Compare):
            left=self.expression(node.left,env)
            for op,item in zip(node.ops,node.comparators):
                right=self.expression(item,env)
                if type(op) not in self.CMP: raise UnsupportedCode('Unsupported comparison')
                if not self.CMP[type(op)](left,right): return False
                left=right
            return True
        if isinstance(node,ast.IfExp): return self.expression(node.body if self.expression(node.test,env) else node.orelse,env)
        if isinstance(node,ast.Subscript):
            value=self.expression(node.value,env)
            if not isinstance(value,(list,tuple,dict,str)): raise UnsupportedCode('Unsupported indexing')
            return value[self.expression(node.slice,env)]
        if isinstance(node,ast.Call):
            args=[self.expression(x,env) for x in node.args]
            if node.keywords: raise UnsupportedCode('Keyword calls not supported')
            if isinstance(node.func,ast.Name) and node.func.id in self.BUILTINS:
                return self.bounded(self.BUILTINS[node.func.id](*args))
            if isinstance(node.func,ast.Attribute):
                obj=self.expression(node.func.value,env)
                allowed={list:{'append','pop'},set:{'add','remove','discard'},dict:{'get','keys','values','items'}}
                if node.func.attr in allowed.get(type(obj),set()):
                    result=getattr(obj,node.func.attr)(*args)
                    self.bounded(obj)
                    return result
        raise UnsupportedCode('Unsupported syntax: '+type(node).__name__)

    def assign(self,target,value,env):
        if isinstance(target,ast.Name): env[target.id]=self.bounded(value)
        elif isinstance(target,(ast.Tuple,ast.List)):
            if len(target.elts)!=len(value): raise UnsupportedCode('Unpacking mismatch')
            for t,v in zip(target.elts,value): self.assign(t,v,env)
        else: raise UnsupportedCode('Only local variable assignment is supported')

    def block(self,body,env):
        for node in body:
            self.tick()
            if isinstance(node,ast.Return): raise Returned(self.expression(node.value,env) if node.value else None)
            elif isinstance(node,ast.Assign):
                value=self.expression(node.value,env)
                for target in node.targets: self.assign(target,value,env)
            elif isinstance(node,ast.AugAssign) and type(node.op) in self.BIN:
                value=self.expression(ast.BinOp(left=node.target,op=node.op,right=node.value),env)
                self.assign(node.target,value,env)
            elif isinstance(node,ast.If): self.block(node.body if self.expression(node.test,env) else node.orelse,env)
            elif isinstance(node,ast.For):
                values=self.expression(node.iter,env)
                for value in values:
                    self.tick(); self.assign(node.target,value,env); self.block(node.body,env)
                self.block(node.orelse,env)
            elif isinstance(node,ast.While):
                while self.expression(node.test,env): self.tick(); self.block(node.body,env)
                self.block(node.orelse,env)
            elif isinstance(node,ast.Expr): self.expression(node.value,env)
            elif isinstance(node,ast.Pass): pass
            else: raise UnsupportedCode('Unsupported statement: '+type(node).__name__)

    def run(self,code,function,args):
        if len(code)>16000: raise UnsupportedCode('Code size limit reached')
        tree=ast.parse(code)
        if any(isinstance(n,(ast.Import,ast.ImportFrom,ast.ClassDef,ast.Global,ast.Nonlocal,ast.Lambda)) for n in ast.walk(tree)):
            raise UnsupportedCode('Imports, classes, global state and lambdas are not allowed')
        fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function),None)
        if fn is None: raise UnsupportedCode('Required function not found: '+function)
        if len(fn.args.args)!=len(args): raise UnsupportedCode('Function argument count mismatch')
        env=dict(zip([a.arg for a in fn.args.args],args))
        try: self.block(fn.body,env)
        except Returned as r: return r.value
        return None
