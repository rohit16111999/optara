import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./e2e',fullyParallel:false,workers:1,timeout:45000,retries:0,
 use:{baseURL:'http://127.0.0.1:3000',viewport:{width:1440,height:1000},channel:process.platform==='win32'?'chrome':undefined,trace:'retain-on-failure',screenshot:'only-on-failure'},
 reporter:[['list'],['html',{open:'never'}]],
});
