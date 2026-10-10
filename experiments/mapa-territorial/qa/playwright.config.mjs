import {defineConfig} from '@playwright/test';
import path from 'node:path';
const output=process.env.QA_OUTPUT||path.resolve('qa-output');
const site=process.env.QA_SITE;
if(!site)throw new Error('QA_SITE must identify the fully built local candidate');
export default defineConfig({
  testDir:'.',testMatch:'**/*.spec.mjs',fullyParallel:false,workers:1,retries:0,
  timeout:90000,globalTimeout:8*60*1000,expect:{timeout:15000},outputDir:path.join(output,'test-results'),
  reporter:[['list'],['json',{outputFile:path.join(output,'playwright-results.json')}]],
  use:{browserName:'chromium',baseURL:'http://127.0.0.1:4173',headless:true,
    launchOptions:{args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']},
    trace:'off',video:'off',screenshot:'off'},
  webServer:{command:`python3 -m http.server 4173 --bind 127.0.0.1 --directory ${JSON.stringify(site)}`,
    url:'http://127.0.0.1:4173/laboratorio/mapa-territorial/',reuseExistingServer:false,timeout:15000}
});
