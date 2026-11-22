# SpatialDB integration

The existing FinalGIS exchange/readback scripts and Core's proven local publication helper are reused. The source version and immutable FWD/CAS go through the real SpatialDB authored ingest, scene compiler, authenticated publication and canonical readback. The inherited license normalization/provenance-ID fix is included explicitly.

The successful publication version is a95ef036438dbcfea1bdbf4b6d8d2720fed19a85a93e1d9ff93fd45d37b6761a. Access tests actually returned anonymous401 / unrelated-user404. Service restart produced byte-identical canonical readback. The publication is in a new disposable PostGIS fixture, not production. Input FWD SHA is a1bc0bdf6fbe24c6a69c1641ac4c7fac18761d204af82c2012bf15d190704cb5.

Publication state replay validates plan/source identity and persisted readback hashes/assets and returns replay=true. It does not make a second publication request. Failures leave FAILED state and never authorize a world effect. Automatic recovery from every intermediate failure boundary is not implemented. No second authoritative spatial database was created.
