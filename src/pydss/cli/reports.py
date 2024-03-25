"""
CLI to run a pydss project
"""

import click
import json
import os

from terminaltables import SingleTable
from os.path import normpath, basename

@click.argument(
    "project-path",
)

@click.option(
    "-l", "--list-reports",
    help="List all reports for a given project path",
    is_flag=True,
    default=False,
    show_default=True,
)

@click.option(
    "-i", "--index",
    help="View report by index (use -l flag to see list of available reports)",
    default=0,
    show_default=True,
)

@click.option(
    "-s", "--scenario",
    required=False,
    help="Pydss scenario name.",
)

@click.option(
    "-r", "--report",
    required=False,
    help="Pydss report name.",
)
@click.command()

def reports(project_path, list_reports=False, scenario=None, report=None, index=0):
    """Explore and print pydss reports."""
    assert not (list_reports and index), "Both 'list' and 'index' options cannot be set to true at the same time"
    assert os.path.exists(project_path), "The provided project path {} does not exist".format(project_path)
    logsPath = os.path.join(project_path, "Logs")
    assert os.path.exists(logsPath), "No Logs folder in the provided project path.".format(project_path)
    print(logsPath)
    reportList = getAvailableReports(logsPath)
    project = basename(normpath(project_path))
    if list_reports:
        Table = SingleTable(reportList, title="Available pydss reports")
        print("")
        print(Table.table)
    elif index:
        idx, projectName, ScenarioName, ReportName = reportList[index]
        printReport(logsPath, projectName, ScenarioName, ReportName)
    elif project:
        for dx, projectName, ScenarioName, ReportName in reportList[1:]:
            if projectName == project:
                if scenario is None or scenario == ScenarioName:
                    if report is None or report == ReportName:
                        printReport(logsPath, projectName, ScenarioName, ReportName)

def printReport(logsPath, project, scenario, report):
    fileName = "{}__{}__reports.log".format(project, scenario)
    filePath = os.path.join(logsPath, fileName)
    assert os.path.exists(filePath), "Report {} for project: {} / scenario: {} does not exist".format(
        report, project, scenario
    )

    tableData = []
    Keys = {}
    with open(os.path.join(logsPath, fileName), "r") as f:
        for l in f:
            data = json.loads(l.strip())
            if "Report" not in data:
                print("Skipping {}. Not a valid pydss report.".format(fileName))
                return None
            elif data["Report"] == report:
                if report not in Keys:
                    Keys[report] = list(data.keys())
                    Keys[report] = [x for x in Keys[report] if x != "Report"]
                values = []
                for k in Keys[report]:
                    values.append(data[k])
                tableData.append(values)
    tableData.insert(0, Keys[report])
    Table = SingleTable(tableData, title="{} report (Project: {}, Scenario: {})".format(
        report, project, scenario
    ))
    print("")
    print(Table.table)
    return

def getAvailableReports(logsPath):
    logFiles = list(filter(lambda x: '.log' in x, os.listdir(logsPath)))
    reportFiles = [x for x in logFiles if "__reports" in x]
    headings = ["#", "Project", "Scenario", "Report"]
    reportList = [headings]
    reportNumber = 0
    for report in reportFiles:
        project, scenario, _ = report.split("__")
        print(reportNumber, project, scenario, report)
        reportTypes = getReportTypes(logsPath, report)
        if reportTypes is not None:
            for reportTypes in reportTypes:
                reportNumber += 1
                reportList.append([reportNumber, project, scenario, reportTypes])
    return reportList


def getReportTypes(logsPath, reportFile):
    fileName = os.path.join(logsPath, reportFile)
    print(fileName)
    f = open(fileName, "r")
    lines = f.readlines()
    reportTypes = []
    for l in lines:
        data = json.loads(l.strip())
        if "Report" not in data:
            print("Skipping {}. Not a valid pydss report.".format(fileName))
            return None
        else:
            if data["Report"] not in reportTypes:
                reportTypes.append(data["Report"])
    return reportTypes
