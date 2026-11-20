# FinalGIS product identity

**FinalGIS — AI-Native Geographic Intelligence & World Creation** is Finalverse's geographic authoring product. Its GIS foundation is QGIS, clearly credited as an independent open-source upstream. Keep FinalGIS as a distinct product, and build differentiated reviewed GIS/world-creation workflows on that foundation. Do not spend effort renaming mature GIS internals or claim that Finalverse authored QGIS.

The interface uses a dark navy product header, white text and restrained cyan accents. Original user-provided Finalverse artwork supplies the product icon family. `plugin/logo.png` is an unchanged copy of `~/Project2026/Finalverse/Images/Finalverse_logo_07.png`; the existing FinalGIS.icns is retained. New splash layout is rendered by Qt from source and the existing PNG, not an AI mockup. Upstream QGIS marks remain where they describe the foundation or third-party content.

macOS metadata: bundle/display nameFinalGIS; identifier `org.finalverse.finalgis`; product version 0.2.0; native C17 launcher; private named FinalGIS profile. QGIS foundation version remains 3.44.15. Standard project names, file extensions, providers and settings namespaces stay compatible. Existing application/project data is not migrated or silently rewritten.

The native bundle contains the desktop engine/resources, product module, public demo sources, worker/library and GPL/source attribution. The independent native worker still depends on this Mac's pinned Qt 6/GDAL environment. The app is a local ad-hoc-signed development candidate, not a notarized portable installer. macOS arm64 was executed; Windows/Linux metadata proposals are clearly unverified.

[QGIS's brand guidance](https://qgis.org/community/organisation/guidelines/) calls for clear derivative identity and due upstream credit. This work does not claim endorsement or trademark clearance. Preserve [QGIS licensing](https://qgis.org/license/), root COPYING and dependency/data notices before any external distribution.
