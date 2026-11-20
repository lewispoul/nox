'use strict';
const fs = require('node:fs/promises');
const {createHash} = require('node:crypto');
const path = require('node:path');
const url = 'https://raw.githubusercontent.com/cheminfo/bruker-data-test/bb9478262aa3513b64b661ddb2f2697ad86463e6/data/zipped/aspirin-1h.zip';
const expected = 'b919359fcac83e5d2ca82d399123a0d4c2a8fe15c7e71937bfe59a4508bab75e';
(async()=>{
  const response = await fetch(url);
  if (!response.ok) throw Error(`Fixture download HTTP ${response.status}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  if (createHash('sha256').update(bytes).digest('hex') !== expected) throw Error('Fixture checksum mismatch');
  await fs.writeFile(path.join(__dirname, 'aspirin-1h.zip'), bytes);
  console.log(`Downloaded MIT-licensed public Bruker fixture: ${bytes.length} bytes; SHA256 verified.`);
})().catch(e=>{console.error(e.message);process.exitCode=1;});
