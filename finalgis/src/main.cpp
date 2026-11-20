// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Finalverse contributors.
#include "geography.hpp"
#include <QCoreApplication>
#include <QJsonDocument>
#include <QFileInfo>
#include <iostream>
#include <map>
int main(int argc,char **argv) {
 QCoreApplication app(argc,argv);
 try {
  const auto args=app.arguments();
  if(args.size()<2) fgis::fail("Expected inspect, plan, run, fiction, validate, transform, or models");
  std::map<QString,QString> options;
  for(qsizetype i=2;i<args.size();++i) {
   const auto a=args[i];
   if(!a.startsWith("--")||options.contains(a)) fgis::fail("Invalid or duplicate option");
   if(a=="--approve"||a=="--allow-remote") options[a]="true";
   else { if(i+1>=args.size()||args[i+1].startsWith("--")) fgis::fail("Missing option value"); options[a]=args[++i]; }
  }
  const auto get=[&](const char *k,const QString &d=QString()){return options.contains(k)?options.at(k):d;};
  const auto required=[&](const char *k){const auto v=get(k);if(v.isEmpty())fgis::fail(QString("Missing ")+k);return v;};
  QJsonObject result;
  const auto command=args[1];
  if(command=="tool-registry") result=fgis::toolRegistry();
  else if(command=="workflow-plan") result=fgis::workflowPlan(required("--source"),fgis::modelPlan(required("--request"),get("--provider","mock"),get("--model","qwen2.5:0.5b"),get("--endpoint","http://127.0.0.1:11434"),get("--key-file"),options.contains("--allow-remote")));
  else if(command=="workflow-run") {
   if(!options.contains("--approve"))fgis::fail("Explicit local execution approval required");
   result=fgis::workflowRun(required("--source"),required("--output"),fgis::object(fgis::read(required("--plan"),65536)),required("--approved-plan"));
  }
  else if(command=="inspect") result=fgis::inspect(required("--source"));
  else if(command=="models") result=fgis::discover(get("--endpoint","http://127.0.0.1:11434"),options.contains("--allow-remote"));
  else if(command=="plan") result=fgis::modelPlan(required("--request"),get("--provider","mock"),get("--model","qwen2.5:0.5b"),get("--endpoint","http://127.0.0.1:11434"),get("--key-file"),options.contains("--allow-remote"));
  else if(command=="run") {
   if(!options.contains("--approve"))fgis::fail("Review the typed plan and pass --approve to process a new output directory");
   result=fgis::run(required("--source"),required("--output"),fgis::object(fgis::read(required("--plan"),65536)));
  } else if(command=="fiction") {
   if(!options.contains("--approve"))fgis::fail("Fictional generation requires --approve");
   bool ok=false;const auto seed=required("--seed").toUInt(&ok);if(!ok)fgis::fail("Seed must be uint32");
   result=fgis::fictional(required("--output"),seed);
  } else if(command=="validate") result=fgis::validateGlb(required("--asset"));
  else if(command=="transform") {
   const auto parts=required("--xyz").split(',');if(parts.size()!=3)fgis::fail("Three coordinates required");
   double xyz[3];for(int i=0;i<3;++i){bool ok=false;xyz[i]=parts[i].toDouble(&ok);if(!ok)fgis::fail("Invalid coordinate");}
   char error[512]{};if(!fgis_transform(required("--from").toUtf8().constData(),required("--to").toUtf8().constData(),xyz,error,sizeof(error)))fgis::fail(error);
   result={{"xyz",QJsonArray{xyz[0],xyz[1],xyz[2]}}};
  } else fgis::fail("Unknown command");
  const auto bytes=QJsonDocument(result).toJson(QJsonDocument::Compact);
  std::cout<<bytes.constData()<<'\n';return 0;
 }catch(const std::exception &e){std::cerr<<"FinalGIS: "<<e.what()<<'\n';return 1;}
}
