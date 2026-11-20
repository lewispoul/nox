'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const JSZip = require('jszip');
const {fromBruker} = require('nmr-parser');
const {fileCollectionFromZip} = require('filelist-utils');
const filename = path.join(__dirname, 'aspirin-1h.zip');
const expected = 'b919359fcac83e5d2ca82d399123a0d4c2a8fe15c7e71937bfe59a4508bab75e';
const sha = data => createHash('sha256').update(data).digest('hex');
(async()=>{
  const bytes = fs.readFileSync(filename);
  assert.equal(sha(bytes), expected);
  const zip = await JSZip.loadAsync(bytes);
  assert(zip.file('1/acqus')); assert(zip.file('1/fid'));
  assert(!zip.file('1/pdata/1/1r'), 'Fixture must exercise raw FID, not an existing FT spectrum');
  const binary = await zip.file('1/fid').async('nodebuffer');
  const spectra = await fromBruker(await fileCollectionFromZip(bytes));
  assert.equal(spectra.length,1);
  const spectrum = spectra[0];
  assert.equal(spectrum.info.isFid,true);
  assert.equal(spectrum.info.dimension,1);
  assert.deepEqual(spectrum.info.nucleus,['1H']);
  assert.equal(spectrum.meta.BYTORDA,1);
  assert.equal(spectrum.meta.DTYPA,0);
  const data = spectrum.dependentVariables[0].components[0].data;
  const acquiredComplexPoints = binary.length / 8;
  assert.equal(acquiredComplexPoints,8192);
  // Independent binary check: signed 32-bit big-endian, interleaved real/imaginary.
  for(let i=0;i<acquiredComplexPoints;i++){
    assert.equal(data.re[i],binary.readInt32BE(i*8));
    assert.equal(data.im[i],binary.readInt32BE(i*8+4));
  }
  assert.equal(data.re.length,16384);
  assert.equal(data.im.length,16384);
  assert(Array.from(data.re.slice(acquiredComplexPoints)).every(x=>x===0));
  assert(Array.from(data.im.slice(acquiredComplexPoints)).every(x=>x===0));
  // This is an observed upstream defect, deliberately reported rather than accepted as an axis.
  assert(!Number.isFinite(spectrum.dimensions[0].coordinatesOffset.magnitude));
  assert.equal(sha(fs.readFileSync(filename)),expected,'Original ZIP must remain unchanged');
  console.log(JSON.stringify({
    status:'raw-decoding-only-verified', fixtureSHA256:expected,
    zipBytes:bytes.length, fidBytes:binary.length, acquiredComplexPoints,
    decodedRealImagPairsCompared:acquiredComplexPoints,
    parserOutputComplexPoints:data.re.length,
    implicitZeroPaddingPoints:data.re.length-acquiredComplexPoints,
    originFrequencyMHz:spectrum.info.originFrequency,
    acquisitionSpectralWidthHz:spectrum.meta.SW_h,
    warning:'nmr-parser 3.0.3 returns a non-finite coordinatesOffset; no ppm/FT/integration validation claimed',
    processingValidated:false, mobileValidated:false
  },null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
