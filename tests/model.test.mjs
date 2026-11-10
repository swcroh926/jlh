import test from 'node:test';import assert from 'node:assert/strict';import {evaluate,parseIdeas} from '../model.mjs';
test('ignores whitespace and caps input',()=>{assert.deepEqual(parseIdeas('  A \n\n B '),['A','B']);assert.equal(parseIdeas('idea\n'.repeat(25)).length,20)});
test('ranks up to three actual candidates without inventing entries',()=>{assert.equal(evaluate(['one']).length,1);assert.equal(evaluate([]).length,0);const result=evaluate(['a','b','c','d']);assert.equal(result.length,3);assert.ok(result.every((x,i)=>!i||result[i-1].average>=x.average))});
