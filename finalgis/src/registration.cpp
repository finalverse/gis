// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Finalverse contributors.
//
// Ω-XVII.2 geographic registration validation (spatial.validate_registration).
//
// Reads an existing finalverse.geographic-registration/0.2 document (the Ω-XV
// contract; no parallel schema is introduced), recomputes its geographic
// anchor with PROJ from the declared source CRS, the pinned geoid grid and the
// declared datum pipeline, and classifies what the document can honestly
// support. It never upgrades a derived relationship into a surveyed one and it
// never writes world state: MutSea owns authoritative registration.
#include "geography.hpp"

#include <proj.h>

#include <QCryptographicHash>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <cmath>
#include <memory>

namespace fgis {
namespace {

struct Ctx {
  PJ_CONTEXT *c = proj_context_create();
  Ctx() {
    const char *paths[] = {FINALGIS_PROJ_DATA_DIR};
    proj_context_set_search_paths(c, 1, paths);
    proj_context_set_enable_network(c, 0);
  }
  ~Ctx() { proj_context_destroy(c); }
};
struct Pj {
  PJ *p;
  explicit Pj(PJ *x) : p(x) {}
  ~Pj() { if (p) proj_destroy(p); }
};

double number(const QJsonValue &v, const QString &what) {
  if (!v.isDouble() || !std::isfinite(v.toDouble())) fail(what + " must be a finite number");
  return v.toDouble();
}

QJsonObject check(const QString &name, bool pass, const QString &detail) {
  return {{"check", name}, {"pass", pass}, {"detail", detail}};
}

}  // namespace

QJsonObject validateRegistration(const QString &path, const QString &geoidOverride) {
  const QByteArray bytes = read(path, 1 << 20);
  const QJsonObject doc = object(bytes);
  QJsonArray checks;
  bool ok = true;
  auto add = [&](const QString &n, bool pass, const QString &d) {
    checks.append(check(n, pass, d));
    ok &= pass;
  };
  add("schema", doc["schema"].toString() == "finalverse.geographic-registration/0.2", doc["schema"].toString());
  const auto source = doc["source"].toObject(), destination = doc["destination"].toObject(),
             pipeline = doc["pipeline"].toObject(), validation = doc["validation"].toObject(),
             authorization = doc["authorization"].toObject(), provenance = doc["provenance"].toObject();
  const QString crs = source["crs"].toString();
  add("source_crs_declared", crs.startsWith("EPSG:"), crs);
  add("units_metre", source["units"].toString() == "metre", source["units"].toString());
  add("source_axes", source["axes"].toString() == "east,grid_north,up", source["axes"].toString());
  add("destination_frame", destination["frame"].toString() == "region_local_z_up/metre", destination["frame"].toString());
  const auto origin = source["origin"].toArray(), anchor = destination["wgs84_anchor_lon_lat_h"].toArray(),
             offset = destination["region_offset"].toArray();
  if (origin.size() != 3 || anchor.size() != 3 || offset.size() != 3) fail("origin, region_offset and anchor need three values");
  const double E = number(origin[0], "origin easting"), N = number(origin[1], "origin northing"), H = number(origin[2], "origin height");

  // Geoid grid: the pinned digest must match the file actually used.
  const QString geoid = geoidOverride.isEmpty() ? pipeline["vertical_grid_file"].toString() : geoidOverride;
  const QByteArray grid = read(geoid, 64 * 1024 * 1024);
  const QString gridSha = sha(grid);
  add("vertical_grid_digest", gridSha == pipeline["vertical_grid_sha256"].toString(), gridSha);

  Ctx ctx;
  // 1. Projected source -> NAD83(CSRS) geographic, longitude/latitude order.
  Pj toGeo(proj_create_crs_to_crs(ctx.c, crs.toUtf8().constData(), "EPSG:4617", nullptr));
  if (!toGeo.p) fail("no coordinate operation from the source CRS to EPSG:4617");
  Pj toGeoNorm(proj_normalize_for_visualization(ctx.c, toGeo.p));
  PJ_COORD c = proj_coord(E, N, 0, 0);
  PJ_COORD geo = proj_trans(toGeoNorm.p, PJ_FWD, c);
  if (!std::isfinite(geo.xyz.x) || !std::isfinite(geo.xyz.y)) fail("source origin cannot be transformed");
  const double lon = geo.xyz.x, lat = geo.xyz.y;
  // 2. Orthometric -> ellipsoidal with the pinned geoid: h = H + N.
  const QString vg = "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=vgridshift +grids=" +
                     QFileInfo(geoid).absoluteFilePath() + " +multiplier=1 +step +proj=unitconvert +xy_in=rad +xy_out=deg";
  Pj vgrid(proj_create(ctx.c, vg.toUtf8().constData()));
  if (!vgrid.p) fail("geoid grid cannot be used by PROJ");
  PJ_COORD ell = proj_trans(vgrid.p, PJ_FWD, proj_coord(lon, lat, H, 0));
  if (!std::isfinite(ell.xyz.z) || ell.xyz.z == HUGE_VAL) fail("origin lies outside the geoid grid");
  const double undulation = ell.xyz.z - H;
  // 3. Declared datum operation NAD83(CSRS) -> WGS84.
  const QString datum = pipeline["csrs_to_wgs84"].toString();
  Pj helmert(proj_create(ctx.c, datum.toUtf8().constData()));
  if (!helmert.p) fail("declared datum pipeline is not a valid PROJ pipeline");
  PJ_COORD w = proj_trans(helmert.p, PJ_FWD, proj_coord(lon, lat, ell.xyz.z, 0));
  const double alon = number(anchor[0], "anchor longitude"), alat = number(anchor[1], "anchor latitude"),
               ah = number(anchor[2], "anchor height");
  const double m_per_deg = 111319.49079327357;
  const double dx = (w.xyz.x - alon) * m_per_deg * std::cos(alat * M_PI / 180.0), dy = (w.xyz.y - alat) * m_per_deg,
               dz = w.xyz.z - ah;
  const double horizontal = std::hypot(dx, dy);
  add("anchor_reproduces_horizontally", horizontal <= 0.001, QString::number(horizontal, 'g', 6) + " m");
  add("anchor_reproduces_vertically", std::abs(dz) <= 0.001, QString::number(dz, 'g', 6) + " m");
  // 4. Round trip back to the projected origin.
  PJ_COORD back = proj_trans(helmert.p, PJ_INV, w);
  back = proj_trans(vgrid.p, PJ_INV, back);
  PJ_COORD proj_back = proj_trans(toGeoNorm.p, PJ_INV, proj_coord(back.xyz.x, back.xyz.y, 0, 0));
  const double rt = std::hypot(proj_back.xyz.x - E, proj_back.xyz.y - N), rtz = std::abs(back.xyz.z - H);
  add("round_trip", rt <= 0.001 && rtz <= 0.001, QString::number(rt, 'g', 6) + " m horizontal, " + QString::number(rtz, 'g', 6) + " m vertical");

  // 5. Honest classification.
  const bool surveyed = validation["surveyed"].toBool(false);
  const bool epoch = !validation["coordinate_epoch"].isNull() && !validation["coordinate_epoch"].isUndefined();
  const bool sourceAccuracy = validation["source_accuracy_metres"].isDouble();
  const QString scope = authorization["scope"].toString();
  QString registrationClass;
  if (surveyed) {
    const bool supported = epoch && sourceAccuracy && doc.contains("control_points");
    add("surveyed_claim_supported", supported, "a surveyed claim needs an epoch, source accuracy and independent control points");
    registrationClass = supported ? "surveyed" : "invalid_surveyed_claim";
  } else {
    registrationClass = scope == "presentation_only" ? "presentation_only" : "derived_model";
  }
  add("scope_consistent", !(scope != "presentation_only" && !surveyed), "scope=" + scope + ", surveyed=" + (surveyed ? "true" : "false"));

  // The directive's WorldSpatialRegistration view, mapped field by field from
  // the existing contract (no second schema is persisted).
  QJsonObject model{
      {"world_id", doc["world"]},
      {"region_id", doc["region"]},
      {"registration_id", sha(bytes)},
      {"registration_revision", doc["revision"]},
      {"source_horizontal_crs", crs},
      {"source_vertical_crs", source["vertical_datum"]},
      {"coordinate_epoch", validation["coordinate_epoch"]},
      {"world_frame", destination["frame"]},
      {"local_origin", origin},
      {"region_offset", offset},
      {"axis_conventions", QJsonObject{{"source", source["axes"]}, {"destination", destination["axes"]}}},
      {"units", source["units"]},
      {"transform_pipeline", QJsonObject{{"id", pipeline["id"]}, {"projected_to_csrs", pipeline["projected_to_csrs"]},
                                         {"csrs_to_wgs84", datum}, {"vertical", pipeline["vertical_formula"]},
                                         {"vertical_grid_sha256", pipeline["vertical_grid_sha256"]}}},
      {"validation_status", validation["status"]},
      {"accuracy_metadata", QJsonObject{{"surveyed", surveyed}, {"datum_operation_accuracy_metres", validation["datum_operation_accuracy_metres"]},
                                        {"source_accuracy_metres", validation["source_accuracy_metres"]}, {"limitations", validation["limitations"]}}},
      {"provenance", provenance},
      {"authorization", authorization}};
  return {{"operation", "spatial.validate_registration"},
          {"schema", "finalgis.registration-validation/1"},
          {"verdict", ok ? (registrationClass == "surveyed" ? "valid_surveyed_registration" : "valid_" + registrationClass + "_registration") : "invalid"},
          {"registration_class", registrationClass},
          {"authoritative", false},
          {"recomputed", QJsonObject{{"csrs_lon_lat", QJsonArray{lon, lat}}, {"geoid_undulation_m", undulation},
                                     {"ellipsoidal_height_csrs_m", ell.xyz.z}, {"wgs84_lon_lat_h", QJsonArray{w.xyz.x, w.xyz.y, w.xyz.z}}}},
          {"checks", checks},
          {"model", model},
          {"note", "Numerical consistency of a declared relationship; not an independent survey. MutSea owns authoritative registration."}};
}

}  // namespace fgis
