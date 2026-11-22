// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Finalverse contributors.
#include "geography.hpp"
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QCryptographicHash>
#include <QJsonDocument>
#include <QElapsedTimer>
#include <QRegularExpression>
#include <QtEndian>
#include <gdal.h>
#include <ogr_api.h>
#include <ogr_srs_api.h>
#include <cpl_conv.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <memory>
#include <mutex>
#include <type_traits>
#include <vector>

namespace {
using Geom=std::unique_ptr<std::remove_pointer_t<OGRGeometryH>,decltype(&OGR_G_DestroyGeometry)>;
using Srs=std::unique_ptr<std::remove_pointer_t<OGRSpatialReferenceH>,decltype(&OSRDestroySpatialReference)>;
using Transform=std::unique_ptr<std::remove_pointer_t<OGRCoordinateTransformationH>,decltype(&OCTDestroyCoordinateTransformation)>;
Geom geom(OGRGeometryH p){return Geom(p,OGR_G_DestroyGeometry);}
Srs srs(const QString &text) {
 // OSRSetFromUserInput also accepts filenames/URLs. Public tool CRS inputs are
 // authority identifiers only; models and callers cannot turn a transform into
 // an implicit filesystem read or remote CRS fetch.
 static const QRegularExpression authority("^[A-Z][A-Z0-9_]{1,15}:[A-Za-z0-9_.-]{1,32}$");
 if(!authority.match(text).hasMatch())fgis::fail("CRS must be an authority identifier; file and URL CRS inputs are refused");
 static std::once_flag setup;
 std::call_once(setup,[]{const char *paths[]={FINALGIS_PROJ_DATA_DIR,nullptr};OSRSetPROJSearchPaths(paths);OSRSetPROJEnableNetwork(false);});
 Srs p(OSRNewSpatialReference(nullptr),OSRDestroySpatialReference);
 if(text.isEmpty()||text.size()>4096||OSRSetFromUserInput(p.get(),text.toUtf8().constData())!=OGRERR_NONE)fgis::fail("Invalid CRS");
 OSRSetAxisMappingStrategy(p.get(),OAMS_TRADITIONAL_GIS_ORDER);return p;
}
Transform transform(OGRSpatialReferenceH from,OGRSpatialReferenceH to) {
 Transform t(OCTNewCoordinateTransformation(from,to),OCTDestroyCoordinateTransformation);
 if(!t)fgis::fail("No available CRS transformation");return t;
}
void point(OGRCoordinateTransformationH t,double &x,double &y,double &z) {
 if(!OCTTransform(t,1,&x,&y,&z)||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))fgis::fail("Coordinate transform failed");
}
constexpr double originX=300619.334946641,originY=5040809.30754108,extent=130.0;
Geom rectangle(double x,double y,double r) {
 auto ring=geom(OGR_G_CreateGeometry(wkbLinearRing));
 for(auto p:std::array<std::array<double,2>,5>{{{x-r,y-r},{x+r,y-r},{x+r,y+r},{x-r,y+r},{x-r,y-r}}})OGR_G_AddPoint_2D(ring.get(),p[0],p[1]);
 auto result=geom(OGR_G_CreateGeometry(wkbPolygon));OGR_G_AddGeometry(result.get(),ring.get());return result;
}
void mkdirNew(const QString &p) {
 QFileInfo i(p);if(i.exists()||i.isSymLink())fgis::fail("Output must be a new directory");
 if(!QDir().mkpath(p+"/objects"))fgis::fail("Cannot create output");
}
struct Mesh {
 std::vector<float> positions;std::vector<quint32> indices;QString name;std::array<double,4> color;
 quint32 vertex(double east,double north,double up) {
  if(!std::isfinite(east)||!std::isfinite(north)||!std::isfinite(up)||std::abs(east)>10000||std::abs(north)>10000||std::abs(up)>10000)fgis::fail("Unbounded mesh coordinate");
  if(positions.size()>300000)fgis::fail("Mesh vertex budget exceeded");
  auto i=static_cast<quint32>(positions.size()/3);
  positions.insert(positions.end(),{static_cast<float>(east),static_cast<float>(up),static_cast<float>(-north)});return i;
 }
 void triangle(quint32 a,quint32 b,quint32 c){if(a==b||b==c||a==c)fgis::fail("Degenerate indices");indices.insert(indices.end(),{a,b,c});}
};
void append32(QByteArray &b,quint32 value){const auto v=qToLittleEndian(value);b.append(reinterpret_cast<const char*>(&v),4);}
quint32 u32(const QByteArray &b,qsizetype off) {if(off<0||off+4>b.size())fgis::fail("Truncated binary");return qFromLittleEndian<quint32>(reinterpret_cast<const uchar*>(b.constData()+off));}
QByteArray glb(const std::vector<Mesh> &meshes) {
 QJsonArray nodes,accessors,views,modelMeshes,materials;QByteArray bin;
 for(const auto &mesh:meshes) {
  if(mesh.indices.empty())continue;
  const auto vi=views.size(),ai=accessors.size();
  const auto posStart=bin.size();
  std::array<double,3> minimum{1e100,1e100,1e100},maximum{-1e100,-1e100,-1e100};
  for(size_t j=0;j<mesh.positions.size();++j){quint32 bits;std::memcpy(&bits,&mesh.positions[j],4);append32(bin,bits);minimum[j%3]=std::min(minimum[j%3],double(mesh.positions[j]));maximum[j%3]=std::max(maximum[j%3],double(mesh.positions[j]));}
  views.append(QJsonObject{{"buffer",0},{"byteOffset",posStart},{"byteLength",bin.size()-posStart},{"target",34962}});
  accessors.append(QJsonObject{{"bufferView",vi},{"componentType",5126},{"count",qint64(mesh.positions.size()/3)},{"type","VEC3"},{"min",QJsonArray{minimum[0],minimum[1],minimum[2]}},{"max",QJsonArray{maximum[0],maximum[1],maximum[2]}}});
  const auto idxStart=bin.size();for(auto i:mesh.indices)append32(bin,i);
  views.append(QJsonObject{{"buffer",0},{"byteOffset",idxStart},{"byteLength",bin.size()-idxStart},{"target",34963}});
  accessors.append(QJsonObject{{"bufferView",vi+1},{"componentType",5125},{"count",qint64(mesh.indices.size())},{"type","SCALAR"}});
  std::vector<double> normals(mesh.positions.size(),0.0);
  for(size_t t=0;t<mesh.indices.size();t+=3){
   const auto a=size_t(mesh.indices[t])*3,b=size_t(mesh.indices[t+1])*3,c=size_t(mesh.indices[t+2])*3;
   std::array<double,3> u{},v{},n{};
   for(int k=0;k<3;k++){u[k]=double(mesh.positions[b+k])-mesh.positions[a+k];v[k]=double(mesh.positions[c+k])-mesh.positions[a+k];}
   n={u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]};
   for(auto i:{a,b,c})for(int k=0;k<3;k++)normals[i+k]+=n[k];
  }
  const auto normalStart=bin.size();
  for(size_t i=0;i<normals.size();i+=3){
   double length=std::hypot(normals[i],normals[i+1],normals[i+2]);if(!std::isfinite(length)||length<1e-20)fgis::fail("Invalid generated surface normal");
   for(int k=0;k<3;k++){float value=static_cast<float>(normals[i+k]/length);quint32 bits;std::memcpy(&bits,&value,4);append32(bin,bits);}
  }
  views.append(QJsonObject{{"buffer",0},{"byteOffset",normalStart},{"byteLength",bin.size()-normalStart},{"target",34962}});
  accessors.append(QJsonObject{{"bufferView",vi+2},{"componentType",5126},{"count",qint64(normals.size()/3)},{"type","VEC3"}});
  const auto mi=materials.size();materials.append(QJsonObject{{"name",mesh.name},{"doubleSided",true},{"pbrMetallicRoughness",QJsonObject{{"baseColorFactor",QJsonArray{mesh.color[0],mesh.color[1],mesh.color[2],mesh.color[3]}},{"metallicFactor",0.0},{"roughnessFactor",0.85}}}});
  modelMeshes.append(QJsonObject{{"name",mesh.name},{"primitives",QJsonArray{QJsonObject{{"attributes",QJsonObject{{"POSITION",ai},{"NORMAL",ai+2}}},{"indices",ai+1},{"material",mi},{"mode",4}}}}});
  nodes.append(QJsonObject{{"name",mesh.name},{"mesh",modelMeshes.size()-1}});
 }
 QJsonArray nodeIds;for(qsizetype i=0;i<nodes.size();++i)nodeIds.append(i);
 QJsonObject doc{{"asset",QJsonObject{{"version","2.0"},{"generator","FinalGIS 0.2.0"}}},{"scene",0},{"scenes",QJsonArray{QJsonObject{{"nodes",nodeIds}}}},{"nodes",nodes},{"meshes",modelMeshes},{"materials",materials},{"accessors",accessors},{"bufferViews",views},{"buffers",QJsonArray{QJsonObject{{"byteLength",bin.size()}}}}};
 auto json=QJsonDocument(doc).toJson(QJsonDocument::Compact);while(json.size()%4)json.append(' ');while(bin.size()%4)bin.append('\0');
 QByteArray result;append32(result,0x46546c67);append32(result,2);append32(result,quint32(28+json.size()+bin.size()));append32(result,quint32(json.size()));append32(result,0x4e4f534a);result+=json;append32(result,quint32(bin.size()));append32(result,0x004e4942);result+=bin;return result;
}
struct Terrain {
 GDALDatasetH ds=nullptr;std::vector<double> data;int width=0,height=0;double inv[6]{};
 Srs projected=srs("EPSG:2950"),raster=srs("EPSG:3979");Transform tx{nullptr,OCTDestroyCoordinateTransformation};
 explicit Terrain(const QString &path) {
  ds=GDALOpenEx(path.toUtf8().constData(),GDAL_OF_RASTER|GDAL_OF_READONLY,nullptr,nullptr,nullptr);if(!ds)fgis::fail("Cannot read elevation dataset");
  width=GDALGetRasterXSize(ds);height=GDALGetRasterYSize(ds);
  if(width<2||height<2||width>2048||height>2048)fgis::fail("Raster budget exceeded");
  double gt[6];if(GDALGetGeoTransform(ds,gt)!=CE_None||!GDALInvGeoTransform(gt,inv))fgis::fail("Invalid raster transform");
  if(OSRSetFromUserInput(raster.get(),GDALGetProjectionRef(ds))!=OGRERR_NONE)fgis::fail("Missing raster CRS");
  OSRSetAxisMappingStrategy(raster.get(),OAMS_TRADITIONAL_GIS_ORDER);tx=transform(projected.get(),raster.get());
  data.resize(size_t(width)*size_t(height));
  if(GDALRasterIO(GDALGetRasterBand(ds,1),GF_Read,0,0,width,height,data.data(),width,height,GDT_Float64,0,0)!=CE_None)fgis::fail("Elevation read failed");
 }
 ~Terrain(){if(ds)GDALClose(ds);}
 double sample(double x,double y) {
  double z=0;point(tx.get(),x,y,z);double px=inv[0]+inv[1]*x+inv[2]*y,py=inv[3]+inv[4]*x+inv[5]*y;
  int ix=int(std::floor(px)),iy=int(std::floor(py));if(ix<0||iy<0||ix>=width||iy>=height)fgis::fail("Elevation coverage incomplete");
  double h=data[size_t(iy)*size_t(width)+size_t(ix)];int ok=0;auto nodata=GDALGetRasterNoDataValue(GDALGetRasterBand(ds,1),&ok);
  if(!std::isfinite(h)||(ok&&h==nodata)||h< -100||h>1000)fgis::fail("Invalid elevation sample");return h;
 }
};
std::vector<Geom> features(const QString &path,OGRSpatialReferenceH target,const char *declared) {
 const auto doc=fgis::object(fgis::read(path));if(doc.value("source_crs").toString()!=declared)fgis::fail("Source CRS does not match pinned declaration");
 const auto fs=doc.value("features").toArray();if(fs.isEmpty()||fs.size()>4096)fgis::fail("Feature budget exceeded");
 auto source=srs(doc.value("source_crs").toString());auto tx=transform(source.get(),target);std::vector<Geom> output;
 for(const auto &f:fs){auto g=geom(OGR_G_CreateGeometryFromJson(QJsonDocument(f.toObject().value("geometry").toObject()).toJson(QJsonDocument::Compact).constData()));
  if(!g||!OGR_G_IsValid(g.get()))fgis::fail("Invalid source geometry");
  if(OGR_G_Transform(g.get(),tx.get())!=OGRERR_NONE)fgis::fail("Geometry reprojection failed");output.push_back(std::move(g));}
 return output;
}
void polygonMesh(OGRGeometryH g,Mesh &mesh,Terrain &terrain,double z0,double height) {
 const auto type=wkbFlatten(OGR_G_GetGeometryType(g));
 if(type==wkbMultiPolygon||type==wkbGeometryCollection){for(int i=0;i<OGR_G_GetGeometryCount(g);++i)polygonMesh(OGR_G_GetGeometryRef(g,i),mesh,terrain,z0,height);return;}
 if(type!=wkbPolygon||OGR_G_IsEmpty(g))return;
 auto center=geom(OGR_G_CreateGeometry(wkbPoint));if(OGR_G_Centroid(g,center.get())!=OGRERR_NONE)fgis::fail("Centroid failed");
 const auto base=terrain.sample(OGR_G_GetX(center.get(),0),OGR_G_GetY(center.get(),0))-z0+0.06;
 auto triangles=geom(OGR_G_ConstrainedDelaunayTriangulation(g));if(!triangles)fgis::fail("GEOS triangulation failed");
 for(int k=0;k<OGR_G_GetGeometryCount(triangles.get());++k){auto tri=OGR_G_GetGeometryRef(triangles.get(),k);auto ring=OGR_G_GetGeometryRef(tri,0);if(!ring||OGR_G_GetPointCount(ring)!=4)fgis::fail("Invalid triangulation result");
  std::array<quint32,3> ids{};for(int j=0;j<3;++j)ids[j]=mesh.vertex(OGR_G_GetX(ring,j)-originX,OGR_G_GetY(ring,j)-originY,base+height);
  const double cross=(OGR_G_GetX(ring,1)-OGR_G_GetX(ring,0))*(OGR_G_GetY(ring,2)-OGR_G_GetY(ring,0))-(OGR_G_GetY(ring,1)-OGR_G_GetY(ring,0))*(OGR_G_GetX(ring,2)-OGR_G_GetX(ring,0));
  if(cross>0)mesh.triangle(ids[0],ids[1],ids[2]);else mesh.triangle(ids[0],ids[2],ids[1]);}
 if(height>0)for(int r=0;r<OGR_G_GetGeometryCount(g);++r){auto ring=OGR_G_GetGeometryRef(g,r);for(int j=0;j+1<OGR_G_GetPointCount(ring);++j){double x=OGR_G_GetX(ring,j)-originX,y=OGR_G_GetY(ring,j)-originY,x1=OGR_G_GetX(ring,j+1)-originX,y1=OGR_G_GetY(ring,j+1)-originY;
  if(std::hypot(x-x1,y-y1)<1e-6)continue;
  auto a=mesh.vertex(x,y,base),b=mesh.vertex(x1,y1,base),c=mesh.vertex(x1,y1,base+height),d=mesh.vertex(x,y,base+height);mesh.triangle(a,b,c);mesh.triangle(a,c,d);}}
}
}

extern "C" const char *fgis_version(){return "0.1.0";}
extern "C" int fgis_transform(const char *from,const char *to,double xyz[3],char *error,size_t cap) {
 try{if(!from||!to||!xyz)fgis::fail("Null transform argument");for(int i=0;i<3;++i)if(!std::isfinite(xyz[i])||std::abs(xyz[i])>1e15)fgis::fail("Invalid coordinate");
  auto a=srs(from),b=srs(to);auto tx=transform(a.get(),b.get());double x=xyz[0],y=xyz[1],z=xyz[2];point(tx.get(),x,y,z);xyz[0]=x;xyz[1]=y;xyz[2]=z;return 1;
 }catch(const std::exception &e){if(error&&cap){const auto n=std::min(cap-1,strlen(e.what()));memcpy(error,e.what(),n);error[n]=0;}return 0;}
}
namespace fgis {
QByteArray read(const QString &path,qint64 limit) {
 QFileInfo i(path);if(!i.isFile()||i.isSymLink()||i.size()>limit)fail("Input must be a bounded local regular file");
 QFile f(path);if(!f.open(QIODevice::ReadOnly))fail("Cannot read input");auto data=f.read(limit+1);if(data.size()>limit)fail("Input exceeded budget");return data;
}
QJsonObject object(const QByteArray &data){QJsonParseError e;auto d=QJsonDocument::fromJson(data,&e);if(e.error!=QJsonParseError::NoError||!d.isObject())fail("Expected JSON object");return d.object();}
QString sha(const QByteArray &data){return QCryptographicHash::hash(data,QCryptographicHash::Sha256).toHex();}
void writeNew(const QString &path,const QByteArray &data) {QFile f(path);if(!f.open(QIODevice::WriteOnly|QIODevice::NewOnly))fail("Refused existing or inaccessible output");if(f.write(data)!=data.size()||!f.flush())fail("Output write failed");}
QJsonObject inspect(const QString &source) {
 GDALAllRegister();auto recipe=object(read(source+"/recipe.json",65536));auto files=recipe.value("files").toObject();
 for(const auto &name:QStringList{"buildings.geojson","roads.geojson","dtm.tif","sources.json","ATTRIBUTION.md"}) {
  auto bytes=read(source+"/"+name);auto lock=files.value(name).toObject();if(lock.value("sha256").toString()!=sha(bytes)||lock.value("byte_length").toInteger()!=bytes.size())fail("Dataset integrity failure: "+name);
 }
 auto target=srs("EPSG:2950");auto buildings=features(source+"/buildings.geojson",target.get(),"EPSG:2950"),roads=features(source+"/roads.geojson",target.get(),"EPSG:4326");
 return {{"schema","finalgis.dataset-inspection/1"},{"dataset_id",recipe.value("dataset_id")},{"source_bundle_recipe_sha256",sha(read(source+"/recipe.json"))},{"buildings",qint64(buildings.size())},{"roads",qint64(roads.size())},{"building_crs","EPSG:2950"},{"road_crs","EPSG:4326"},{"processing_crs","EPSG:2950"},{"axis_order","x=easting,y=northing; GIS lon,lat order for geodetic input"},{"license","CC-BY-4.0 AND OGL-Canada-2.0"},{"source_classification","verified source snapshots; accuracy not certified"},{"gdal",GDALVersionInfo("RELEASE_NAME")}};
}
QJsonObject plan(const QString &request) {
 if(request.trimmed().isEmpty()||request.size()>2048)fail("Request must contain 1..2048 characters");
 return {{"schema","finalgis.typed-plan/1"},{"request",request},{"operations",QJsonArray{QJsonObject{{"tool","inspect"}},QJsonObject{{"tool","clip_project"},{"target_crs","EPSG:2950"},{"half_extent_metres",130}},QJsonObject{{"tool","road_buffer"},{"radius_metres",2.5}},QJsonObject{{"tool","generate"},{"building_height_metres",12},{"terrain_grid",33}}}},{"publication","review_required"}};
}
void validatePlan(const QJsonObject &p) {
 if(p.value("schema")!="finalgis.typed-plan/1"||p.value("request").toString().isEmpty()||p.value("request").toString().size()>2048||p.value("publication")!="review_required")fail("Invalid plan contract");
 for(auto it=p.begin();it!=p.end();++it)if(!QStringList{"schema","request","operations","publication","planning"}.contains(it.key()))fail("Unknown plan field");
 const auto ops=p.value("operations").toArray();if(ops.size()!=4)fail("Exactly four bounded operations required");
 auto expected=plan(p.value("request").toString()).value("operations").toArray();
 if(ops!=expected)fail("Unapproved tool, CRS, extent, unit or parameter; this milestone admits only the reviewed Montréal recipe");
}
QJsonObject validateGlb(const QString &path) {
 auto b=read(path,16*1024*1024);
 if(b.size()<28||u32(b,0)!=0x46546c67||u32(b,4)!=2||u32(b,8)!=quint32(b.size())||u32(b,16)!=0x4e4f534a)fail("Invalid GLB header");
 const auto n=u32(b,12);if(n%4||n>quint32(b.size()-28))fail("Invalid JSON chunk");
 const auto json=object(b.mid(20,n));auto accessors=json.value("accessors").toArray(),views=json.value("bufferViews").toArray();
 const auto offset=qsizetype(n)+28;if(u32(b,n+24)!=0x004e4942||u32(b,n+20)!=quint32(b.size()-offset))fail("Invalid binary chunk");
 if(json.value("buffers").toArray().size()!=1||json.value("buffers").toArray()[0].toObject().contains("uri"))fail("External buffer refused");
 qint64 vertices=0,triangles=0;
 for(const auto &m:json.value("meshes").toArray())for(const auto &p:m.toObject().value("primitives").toArray()) {
  const auto primitive=p.toObject();if(primitive.value("mode").toInt(4)!=4)fail("Only triangles supported");
  auto pi=primitive.value("attributes").toObject().value("POSITION").toInt(-1),ii=primitive.value("indices").toInt(-1);
  if(pi<0||ii<0||pi>=accessors.size()||ii>=accessors.size())fail("Invalid accessor index");
  auto pos=accessors[pi].toObject(),idx=accessors[ii].toObject();
  if(pos.value("componentType")!=5126||pos.value("type")!="VEC3"||idx.value("componentType")!=5125||idx.value("type")!="SCALAR")fail("Unsupported generated accessor");
  const auto pc=pos.value("count").toInteger(),ic=idx.value("count").toInteger();if(pc<3||pc>100000||ic<3||ic>300000||ic%3)fail("Geometry count budget");
  auto pv=pos.value("bufferView").toInt(-1),iv=idx.value("bufferView").toInt(-1);if(pv<0||iv<0||pv>=views.size()||iv>=views.size())fail("Invalid buffer view");
  auto span=[&](const QJsonObject &v,qint64 length){auto start=v.value("byteOffset").toInteger(),size=v.value("byteLength").toInteger();if(start<0||size<length||start+size>b.size()-offset||v.value("buffer").toInt()!=0)fail("Binary bounds failure");return offset+start;};
  const auto po=span(views[pv].toObject(),pc*12),io=span(views[iv].toObject(),ic*4);
  for(qint64 i=0;i<pc*3;++i){auto bits=u32(b,po+i*4);float f;memcpy(&f,&bits,4);if(!std::isfinite(f)||std::abs(f)>10000)fail("Nonfinite or unbounded vertex");}
  for(qint64 i=0;i<ic;++i)if(u32(b,io+i*4)>=pc)fail("Index out of range");vertices+=pc;triangles+=ic/3;
 }
 if(!vertices||vertices>200000||triangles>200000)fail("Empty or oversized mesh");
 return {{"sha256",sha(b)},{"bytes",b.size()},{"vertices",vertices},{"triangles",triangles},{"glb_version",2},{"axes","glTF Y-up: (east,up,-grid_north)"},{"validation","bounded finite indexed triangles"}};
}
QJsonObject run(const QString &source,const QString &output,const QJsonObject &p) {
 validatePlan(p);QElapsedTimer timer;timer.start();auto metadata=inspect(source);auto importNs=timer.nsecsElapsed();
 auto target=srs("EPSG:2950");auto buildings=features(source+"/buildings.geojson",target.get(),"EPSG:2950"),roads=features(source+"/roads.geojson",target.get(),"EPSG:4326");
 Terrain terrain(source+"/dtm.tif");const auto z0=terrain.sample(originX,originY);auto boundary=rectangle(originX,originY,extent);
 Mesh ground{{},{},"NRCan terrain — resampled derived",{0.25,0.38,0.27,1}},houses{{},{},"Montréal roofs — estimated 12m massing",{0.72,0.55,0.38,1}},streets{{},{},"Road centerline buffer — illustrative 5m corridor",{0.27,0.32,0.38,1}};
 constexpr int n=33;
 for(int y=0;y<n;++y)for(int x=0;x<n;++x){const double e=-extent+2*extent*x/(n-1),north=-extent+2*extent*y/(n-1);ground.vertex(e,north,terrain.sample(originX+e,originY+north)-z0);}
 for(int y=0;y<n-1;++y)for(int x=0;x<n-1;++x){auto a=quint32(y*n+x),b=a+1,c=a+n,d=c+1;ground.triangle(a,b,c);ground.triangle(b,d,c);}
 qint64 included=0;QJsonArray featureReceipts;
 for(auto &g:buildings){auto clipped=geom(OGR_G_Intersection(g.get(),boundary.get()));if(!clipped||OGR_G_IsEmpty(clipped.get()))continue;if(!OGR_G_IsValid(clipped.get()))fail("Clipped footprint invalid");
  polygonMesh(clipped.get(),houses,terrain,z0,12);++included;featureReceipts.append(QJsonObject{{"kind","building_proxy"},{"source_geometry","roof_outline"},{"height_metres",12},{"height_classification","procedural"},{"area_square_metres",OGR_G_Area(clipped.get())}});}
 qint64 buffered=0;double corridorArea=0;
 for(auto &g:roads){auto clipped=geom(OGR_G_Intersection(g.get(),boundary.get()));if(!clipped||OGR_G_IsEmpty(clipped.get()))continue;
  auto buffer=geom(OGR_G_Buffer(clipped.get(),2.5,4));if(!buffer||!OGR_G_IsValid(buffer.get()))fail("Road buffer invalid");auto bounded=geom(OGR_G_Intersection(buffer.get(),boundary.get()));if(!bounded)fail("Buffer clipping failed");
  corridorArea+=OGR_G_Area(bounded.get());polygonMesh(bounded.get(),streets,terrain,z0,0);++buffered;}
 if(included==0||buffered==0)fail("No source geometry in selected area");
 const auto geometryNs=timer.nsecsElapsed()-importNs;auto bytes=glb({ground,houses,streets});mkdirNew(output);const auto asset=sha(bytes);writeNew(output+"/objects/"+asset,bytes);writeNew(output+"/scene.glb",bytes);
 auto validation=validateGlb(output+"/scene.glb");
 auto receipt=QJsonObject{{"schema","finalgis.workflow/1"},{"generator","FinalGIS native GDAL/PROJ/GEOS"},{"version","0.2.0"},{"mode","reality_constrained"},{"seed",0},{"dataset",metadata},{"plan",p},{"asset",validation},{"frame",QJsonObject{{"id","montreal-finalgis-mtm8-offset"},{"kind","local_cartesian"},{"crs","EPSG:2950 with CGVD2013 orthometric vertical values; projected offset"},{"units","metre"},{"axes","east,grid_north,up"},{"origin_projected",QJsonArray{originX,originY,z0}},{"geodetic_anchor",QJsonArray{-73.55350350168884,45.507201203216475}},{"model_to_frame","glTF (x,y,z) -> (x,-z,y)"}}},{"area_extent_metres",260},{"included_building_proxies",included},{"buffered_road_segments",buffered},{"corridor_sum_area_square_metres",corridorArea},{"corridor_note","Illustrative buffered centerlines; overlapping areas counted, no walkability or routing certification"},{"features",featureReceipts},{"provenance",QJsonDocument::fromJson(read(source+"/sources.json")).array()},{"attribution",QString::fromUtf8(read(source+"/ATTRIBUTION.md"))},{"accuracy_note","Roof outlines and DEM are content-pinned source-derived; flat roofs, constant 12m heights, colors and corridor widths are synthetic. No surveyed facades or validated ecological/urban simulation."},{"timings_ms",QJsonObject{{"dataset_validation",double(importNs)/1e6},{"geometry",double(geometryNs)/1e6},{"export_and_validation",double(timer.nsecsElapsed()-importNs-geometryNs)/1e6},{"total",double(timer.nsecsElapsed())/1e6}}},{"publication","offline_export_only"}};
 writeNew(output+"/workflow.json",QJsonDocument(receipt).toJson(QJsonDocument::Indented));return receipt;
}
QJsonObject fictional(const QString &output,quint32 seed) {
 QElapsedTimer timer;timer.start();Mesh terrain{{},{},"Aetheria procedural terrain",{0.23,0.48,0.42,1}},water{{},{},"Aetheria imaginary lake",{0.1,0.32,0.62,1}};
 constexpr int n=33;auto sample=[&](double x,double y){return 4*std::sin(x/30.0+double(seed%1000)/1000)*std::cos(y/35.0)+0.01*(x*x+y*y)/40;};
 for(int y=0;y<n;++y)for(int x=0;x<n;++x){double e=-100+200.0*x/(n-1),north=-100+200.0*y/(n-1);terrain.vertex(e,north,sample(e,north));}
 for(int y=0;y<n-1;++y)for(int x=0;x<n-1;++x){auto a=quint32(y*n+x),b=a+1,c=a+n,d=c+1;terrain.triangle(a,b,c);terrain.triangle(b,d,c);}
 for(auto p:std::array<std::array<double,2>,4>{{{-24,-15},{24,-15},{24,15},{-24,15}}})water.vertex(p[0],p[1],4.5);
 water.triangle(0,1,2);water.triangle(0,2,3);mkdirNew(output);auto bytes=glb({terrain,water});auto asset=sha(bytes);writeNew(output+"/objects/"+asset,bytes);writeNew(output+"/scene.glb",bytes);
 auto r=QJsonObject{{"schema","finalgis.workflow/1"},{"generator","FinalGIS fictional heightfield"},{"version","0.2.0"},{"mode","fictional"},{"seed",qint64(seed)},{"asset",validateGlb(output+"/scene.glb")},{"frame",QJsonObject{{"id","aetheria-finalgis-local"},{"kind","local_cartesian"},{"crs","Aetheria arbitrary local Cartesian, no Earth ellipsoid"},{"units","metre"},{"axes","east,north,up"},{"model_to_frame","glTF (x,y,z) -> (x,-z,y)"}}},{"semantics",QJsonArray{"fictional_terrain","imaginary_lake; decorative water plane, no hydrology model"}},{"elapsed_ms",double(timer.nsecsElapsed())/1e6},{"publication","offline_export_only"}};
 writeNew(output+"/workflow.json",QJsonDocument(r).toJson(QJsonDocument::Indented));return r;
}
}
