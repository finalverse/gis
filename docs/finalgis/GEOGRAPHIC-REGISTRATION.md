# Geographic registration and limits

Source roofs use EPSG:2950, roads EPSG:4326, DEM EPSG:3979 with CGVD2013 orthometric heights. Native operations retain GIS x/y order and produce east/grid-north/up offsets with a double-precision projected origin; glTF is (east,up,-grid-north). GPU coordinates stay local. Flat roofs,12m heights, colors and corridor widths are synthetic. Geoid heights are not silently substituted.

Standalone scene publication has no authoritative world registration. It is labeled source-derived projected offsets. The existing Ω-XV registration contract is reused only for presentation composition with resident bodies in a new copied world. That contract uses the pinned CGG2013a grid and PROJ datum pipeline; surveyed accuracy and coordinate epoch remain unresolved. MutSea's authoritative geographic descriptor is unchanged. Existing control/roundtrip evidence is prior evidence, not a new survey.

The viewer preparation stores registration digest, publication version and real owner-authorized static-reference receipts. It does not turn the presentation relationship into surveyed alignment. Wrong CRS, units and vertical datum are refused by native plan validation. Source compatibility tests still exercise numeric coordinate roundtrips. No scientific fidelity, physical navigation certification or cadastral ownership is claimed.
