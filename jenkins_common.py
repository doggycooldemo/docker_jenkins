from __future__ import print_function
import requests
import common
from jinja2 import Environment, FileSystemLoader
import os
import json
import time

def addJob(name, repoUrl):
    thisDir = os.path.dirname(os.path.abspath(__file__))
    j2 = Environment(loader=FileSystemLoader(thisDir), trim_blocks=True)
    content = j2.get_template('templates/config.xml').render(name=name, repo_url=repoUrl)
    headers = {"Content-Type": "text/xml; charset=UTF-8"}
    r = requests.post(common.jenkinsUrl() + "createItem?name=" + name, data=content, headers=headers)
    if r.status_code != 200:
        raise Exception("Failed to add job; status was " + str(r.status_code))

def runJob(job, branch):
    requests.post(common.jenkinsUrl() + "job/" + job + "/job/" + branch + "/build?delay=0sec")

def waitForBuild(job, branch):
    buildId = waitForBuildToExist(job, branch)
    if buildId == None:
        return None
    status = -1
    count = 300
    while status != 200 and count >= 0:
        count = count - 1
        resp = requests.get(common.jenkinsUrl() + "job/" + job + "/job/" + branch + "/" + str(buildId) + "/api/json")
        status = resp.status_code
        if status == 200:
            j = json.loads(resp.text)
            if j['result'] != None and len(j['result'].strip()) > 0:
                return j
            else:
                status = -1
                time.sleep(1)
    return None

def getArtifact(job, branch, buildId, relativePath):
    print(common.jenkinsUrl() + "job/" + job + "/job/" + branch + "/" + str(buildId) + "/artifact/" + relativePath)
    resp = requests.get(common.jenkinsUrl() + "job/" + job + "/job/" + branch + "/" + str(buildId) + "/artifact/" + relativePath)
    if resp.status_code != 200:
        raise Exception("Failed to retrieve artifact " + str(resp.status_code))
    return resp.text


def waitForBuildToExist(job, branch):
    status = -1
    count = 60
    while status != 200 and count >= 0:
        count = count - 1
        resp = requests.get(common.jenkinsUrl() + "job/" + job + "/job/" + branch + "/api/json")
        status = resp.status_code
        if status == 200:
            j = json.loads(resp.text)
            if len(j['builds']) == 0:
                status = -1
                time.sleep(1)
            else:
                return j['builds'][0]['number']
    return None

def scanMultibranchPipeline(job):
    r = requests.post(common.jenkinsUrl() + "job/" + job + "/build?delay=0")
    if r.status_code != 200:
        raise Exception("Failed scan multibranch pipeline " + str(r.status_code))

def addUsernamePasswordCredential(id, username, password):
    template = """
import com.cloudbees.plugins.credentials.impl.*;
import com.cloudbees.plugins.credentials.*;
import com.cloudbees.plugins.credentials.domains.*;
Credentials c = (Credentials) new UsernamePasswordCredentialsImpl(CredentialsScope.GLOBAL,"{0}", "description", "{1}", "{2}")
SystemCredentialsProvider.getInstance().getStore().addCredentials(Domain.global(), c)
"""

    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    r = requests.post(common.jenkinsUrl() + "scriptText", data={'script': template.format(id, username, password)}, headers=headers)
    if r.status_code != 200:
        raise Exception("Failed to set credential; status was " + str(r.status_code))

def clearAllJobs():
    template = """
import hudson.matrix.*
import jenkins.model.*;
import com.cloudbees.hudson.plugins.folder.*
while (Jenkins.getInstance().getAllItems().size() > 0) {
    Jenkins.getInstance().getAllItems()[0].delete()
}
"""
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    r = requests.post(common.jenkinsUrl() + "scriptText", data={'script': template}, headers=headers)
    if r.status_code != 200:
        raise Exception("Failed to clear all jobs; status was " + str(r.status_code))

def addEnvVar(name, value):
    template = """
import hudson.slaves.EnvironmentVariablesNodeProperty
import jenkins.model.Jenkins

instance = Jenkins.getInstance()
globalNodeProperties = instance.getGlobalNodeProperties()
envVarsNodePropertyList = globalNodeProperties.getAll(EnvironmentVariablesNodeProperty.class)

newEnvVarsNodeProperty = null
envVars = null

if ( envVarsNodePropertyList == null || envVarsNodePropertyList.size() == 0 ) {{
  newEnvVarsNodeProperty = new EnvironmentVariablesNodeProperty();
  globalNodeProperties.add(newEnvVarsNodeProperty)
  envVars = newEnvVarsNodeProperty.getEnvVars()
}} else {{
  envVars = envVarsNodePropertyList.get(0).getEnvVars()
}}

envVars.put("{0}", "{1}")

instance.save()
"""
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    r = requests.post(common.jenkinsUrl() + "scriptText", data={'script': template.format(name, value)}, headers=headers)
    if r.status_code != 200:
        raise Exception("Failed to set env var; status was " + str(r.status_code))

def clearEnvVars():
    template = """
import hudson.slaves.EnvironmentVariablesNodeProperty
import jenkins.model.Jenkins

instance = Jenkins.getInstance()
globalNodeProperties = instance.getGlobalNodeProperties()
envVarsNodePropertyList = globalNodeProperties.getAll(EnvironmentVariablesNodeProperty.class)

newEnvVarsNodeProperty = null
envVars = null

if ( envVarsNodePropertyList == null || envVarsNodePropertyList.size() == 0 ) {
  newEnvVarsNodeProperty = new EnvironmentVariablesNodeProperty();
  globalNodeProperties.add(newEnvVarsNodeProperty)
  envVars = newEnvVarsNodeProperty.getEnvVars()
} else {
  envVars = envVarsNodePropertyList.get(0).getEnvVars()
}

envVars.clear()

instance.save()
"""
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    r = requests.post(common.jenkinsUrl() + "scriptText", data={'script': template}, headers=headers)
    if r.status_code != 200:
        raise Exception("Failed to clear all env vars; status was " + str(r.status_code))

def clearAll():
    clearEnvVars()
    clearAllJobs()
