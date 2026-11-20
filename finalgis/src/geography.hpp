// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Finalverse contributors.
#pragma once
#include "finalgis.h"
#include <QJsonObject>
#include <QJsonArray>
#include <QString>
#include <stdexcept>
namespace fgis {
[[noreturn]] inline void fail(const QString &s) { throw std::runtime_error(s.toStdString()); }
QByteArray read(const QString &path, qint64 limit=32*1024*1024);
QJsonObject object(const QByteArray &bytes);
QString sha(const QByteArray &bytes);
void writeNew(const QString &path,const QByteArray &bytes);
QJsonObject inspect(const QString &source);
QJsonObject plan(const QString &request);
void validatePlan(const QJsonObject &p);
QJsonObject run(const QString &source,const QString &output,const QJsonObject &p);
QJsonObject fictional(const QString &output,quint32 seed);
QJsonObject validateGlb(const QString &path);
QJsonObject modelPlan(const QString &request,const QString &provider,const QString &model,
                      const QString &endpoint,const QString &keyFile,bool allowRemote);
QJsonObject toolRegistry();
QJsonObject workflowPlan(const QString &source,const QJsonObject &legacy);
QJsonObject workflowRun(const QString &source,const QString &output,const QJsonObject &plan,const QString &approval);
QJsonObject discover(const QString &endpoint,bool allowRemote);
}
