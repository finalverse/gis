// SPDX-License-Identifier: GPL-2.0-or-later
#include "geography.hpp"
#include <QJsonDocument>
#include <QFileInfo>
#include <QDir>
namespace fgis
{
  namespace
  {
    QByteArray canonical( const QJsonObject &o )
    {
      return QJsonDocument( o ).toJson( QJsonDocument::Compact );
    }
    QJsonArray sequence()
    {
      return {
        QJsonObject { { "tool", "gis.inspect_dataset" } },
        QJsonObject { { "tool", "gis.transform_crs" }, { "target_crs", "EPSG:2950" } },
        QJsonObject { { "tool", "gis.clip" }, { "half_extent_metres", 130 } },
        QJsonObject { { "tool", "gis.buffer" }, { "radius_metres", 2.5 } },
        QJsonObject { { "tool", "gis.validate_geometry" } },
        QJsonObject { { "tool", "gis.prepare_scene" }, { "building_height_metres", 12 }, { "terrain_grid", 33 } }
      };
    }
    QJsonObject constraints()
    {
      return { { "executor_version", "finalgis.native-scene/0.2-normals" }, { "max_output_bytes", 16777216 }, { "max_operations", 6 }, { "wall_ms", 60000 }, { "cancellation", "host terminates isolated worker; incomplete outputs are not published" } };
    }
    QString identifier( QJsonObject p )
    {
      p.remove( "plan_id" );
      return sha( canonical( p ) );
    }
    void validateWorkflow( const QJsonObject &p, const QJsonObject &dataset )
    {
      const QStringList keys = {
        "schema",
        "plan_id",
        "request_id",
        "model_provider",
        "model_identifier",
        "tool_schema_version",
        "operation_sequence",
        "input_dataset_references",
        "expected_crs",
        "expected_units",
        "expected_vertical_datum",
        "expected_outputs",
        "authorization_scope",
        "execution_constraints",
        "native_plan",
        "registration_status"
      };
      if ( p.size() != keys.size() )
        fail( "Workflow root field count; authority injection refused" );
      for ( const auto &k : keys )
        if ( !p.contains( k ) )
          fail( "Missing workflow field: " + k );
      auto legacy = p.value( "native_plan" ).toObject();
      validatePlan( legacy );
      auto receipt = legacy.value( "planning" ).toObject();
      if (
        p.value( "schema" ) != "finalgis.geographic-plan/2"
        || p.value( "plan_id" ).toString() != identifier( p )
        || p.value( "request_id" ) != sha( legacy.value( "request" ).toString().toUtf8() )
        || p.value( "operation_sequence" ) != sequence()
        || p.value( "input_dataset_references" ) != dataset
        || p.value( "tool_schema_version" ) != "finalgis.gis-tools/1"
        || p.value( "model_provider" ) != receipt.value( "provider" )
        || p.value( "model_identifier" ) != receipt.value( "model" )
        || p.value( "expected_crs" ) != "EPSG:2950"
        || p.value( "expected_units" ) != "metre"
        || p.value( "expected_vertical_datum" ) != "CGVD2013"
        || p.value( "authorization_scope" ) != "local_new_directory_only"
        || p.value( "execution_constraints" ) != constraints()
        || p.value( "expected_outputs" ) != QJsonArray { "scene.glb", "workflow.json" }
        || p.value( "registration_status" ) != "source-derived projected offsets; no authoritative world registration"
      )
        fail( "Workflow scope, dataset, tools, identity or limits mismatch" );
      const auto outcome = receipt.value( "outcome" ).toString();
      if ( !( ( receipt.value( "provider" ) == "mock" && outcome == "deterministic_mock" )
              || ( QStringList { "ollama", "openai" }.contains( receipt.value( "provider" ).toString() ) && outcome == "validated_model_recipe" ) ) )
        fail( "Real provider plan must validate; fallback is not AI acceptance" );
    }
  } //namespace
  QJsonObject toolRegistry()
  {
    QJsonArray tools;
    const QStringList names
      = { "inspect_dataset", "inspect_layers", "inspect_crs", "inspect_extent", "transform_crs", "clip", "buffer", "intersect", "union", "reproject_raster", "sample_elevation", "inspect_topology", "validate_geometry", "generate_terrain", "prepare_scene", "preview_publication" };
    const QStringList executable = { "inspect_dataset", "transform_crs", "clip", "buffer", "validate_geometry", "prepare_scene" };
    for ( const auto &name : names )
    {
      bool enabled = executable.contains( name );
      QJsonObject properties { { "tool", QJsonObject { { "const", "gis." + name } } } };
      if ( name == "transform_crs" )
        properties["target_crs"] = QJsonObject { { "const", "EPSG:2950" } };
      if ( name == "clip" )
        properties["half_extent_metres"] = QJsonObject { { "const", 130 } };
      if ( name == "buffer" )
        properties["radius_metres"] = QJsonObject { { "const", 2.5 } };
      if ( name == "prepare_scene" )
      {
        properties["building_height_metres"] = QJsonObject { { "const", 12 } };
        properties["terrain_grid"] = QJsonObject { { "const", 33 } };
      }
      QJsonObject input = enabled ? QJsonObject { { "type", "object" }, { "additionalProperties", false }, { "properties", properties }, { "required", QJsonArray::fromStringList( properties.keys() ) } }
                                  : QJsonObject { { "not", QJsonObject {} } };
      tools.append(
        QJsonObject {
          { "name", "gis." + name },
          { "status", enabled ? "supported_in_bounded_montreal_recipe" : "deferred_standalone_tool" },
          { "input_schema", input },
          { "output_schema", QJsonObject { { "type", "object" }, { "description", "native receipt with frame and geometry hashes" } } },
          { "units", "metre; geodetic inputs explicitly longitude,latitude" },
          { "crs", "EPSG:2950; input4326 roads and3979 DEM transformed by native tools" },
          { "side_effect", enabled ? "read or new local artifact; never world publication" : "none; refused" },
          { "authorization", "explicit reviewed plan digest and --approve" },
          { "limits", constraints() },
          { "error", "nonzero process status with bounded message" },
          { "provenance", "source recipe hash, original dataset references, native tool receipt" }
        }
      );
    }
    return { { "schema", "finalgis.gis-tools/1" }, { "tools", tools }, { "implementation", "existing native GDAL/OGR/PROJ/GEOS composite recipe; no unrestricted dispatch" } };
  }
  QJsonObject workflowPlan( const QString &source, const QJsonObject &legacy )
  {
    auto dataset = inspect( source );
    validatePlan( legacy );
    auto receipt = legacy.value( "planning" ).toObject();
    QJsonObject p {
      { "schema", "finalgis.geographic-plan/2" },
      { "request_id", sha( legacy.value( "request" ).toString().toUtf8() ) },
      { "model_provider", receipt.value( "provider" ) },
      { "model_identifier", receipt.value( "model" ) },
      { "tool_schema_version", "finalgis.gis-tools/1" },
      { "operation_sequence", sequence() },
      { "input_dataset_references", dataset },
      { "expected_crs", "EPSG:2950" },
      { "expected_units", "metre" },
      { "expected_vertical_datum", "CGVD2013" },
      { "expected_outputs", QJsonArray { "scene.glb", "workflow.json" } },
      { "authorization_scope", "local_new_directory_only" },
      { "execution_constraints", constraints() },
      { "native_plan", legacy },
      { "registration_status", "source-derived projected offsets; no authoritative world registration" }
    };
    p["plan_id"] = identifier( p );
    validateWorkflow( p, dataset );
    return p;
  }
  QJsonObject workflowRun( const QString &source, const QString &output, const QJsonObject &p, const QString &approval )
  {
    validateWorkflow( p, inspect( source ) );
    if ( approval != p.value( "plan_id" ).toString() )
      fail( "Approval must name the exact reviewed plan digest" );
    if ( QFileInfo( output ).exists() )
    {
      if ( QFileInfo( output ).isSymLink() || !QFileInfo( output ).isDir() )
        fail( "Unsafe retry output" );
      auto old = object( read( output + "/workflow.json", 1024 * 1024 ) );
      if ( old.value( "plan" ) != p.value( "native_plan" ) )
        fail( "Immutable job conflict" );
      auto asset = validateGlb( output + "/scene.glb" );
      if ( asset != old.value( "asset" ).toObject() )
        fail( "Retry asset mismatch" );
      old["workflow_plan_id"] = approval;
      old["replay"] = true;
      old["world_mutated"] = false;
      return old;
    }
    auto result = run( source, output, p.value( "native_plan" ).toObject() );
    if ( QFileInfo( output + "/scene.glb" ).size() > 16777216 )
      fail( "Output byte budget exceeded" );
    result["workflow_plan_id"] = approval;
    result["replay"] = false;
    result["world_mutated"] = false;
    writeNew( output + "/geographic-plan.json", QJsonDocument( p ).toJson( QJsonDocument::Indented ) );
    writeNew( output + "/execution.json", QJsonDocument( result ).toJson( QJsonDocument::Indented ) );
    return result;
  }
} //namespace fgis
