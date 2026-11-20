# NOx NMR FID decoding spike

This is a Node-only, raw-decoding proof, not a production processing engine.

```sh
npm ci --ignore-scripts
npm run fetch-fixture
npm test
```

Installation and fixture download need the network. The test does not.
The fixture is a public MIT-licensed Bruker aspirin ¹H ZIP, pinned and hashed.
`verify.cjs` independently compares all 8,192 acquired complex pairs to the raw
big-endian signed-int32 bytes, checks source preservation, and explicitly reports
the old parser's implicit zero-padding and non-finite coordinate metadata.

No Fourier transform, phase, ppm axis, integration, browser or mobile validation
is claimed. See `../docs/nox/NMR_FID_SPIKE.md` for results, licenses and next gates.
The public fixture ZIP and installed dependencies are intentionally untracked.
