#! /usr/bin/env node

/** Upload a theme package (or directory) for a project.
 */

const AdmZip = require('adm-zip')
const axios = require('axios')
const fs = require('fs')
const ini = require('ini')
const path = require('path')
const readline = require('readline')
const FormData = require('form-data')

const CONFIG_FILENAME = `${process.env.HOME}/.djd/credentials`
let CONFIG = {}

const rdl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: true
})

function askQuestion (query) {
  return new Promise(resolve => rdl.question(query, ans => {
    resolve(ans)
  }))
}

function ValueError (msg) {
  return msg
};

async function getProject (project) {
  let updated = false
  if (!project) {
    for (const section in CONFIG) {
      const srcPath = CONFIG[section].src_path
      if (srcPath &&
        path.resolve(srcPath) === path.resolve(process.cwd())) {
        project = section
        break
      }
    }
    if (!project) {
      project = path.basename(process.cwd())
      const customName = await askQuestion(
        'Please enter the name of the project.\n' +
        'By default a project is hosted at *project*.djaoapp.com\n' +
        `(project defaults to ${project}): `)
      if (customName) {
        project = customName
      }
    }
  }

  const srcPath = (CONFIG[project] || {}).src_path || ''
  if (!srcPath ||
    !(path.resolve(srcPath) === path.resolve(process.cwd()))) {
    if (!(project in CONFIG)) {
      CONFIG[project] = { srcPath: '' }
    }
    CONFIG[project].srcPath = process.cwd()
    updated = true
  }

  return { name: project, updated }
}

/** Required base_url and api_key to connect to the URL endpoint.
 */
async function getProjectConnect (project, baseUrl, apiKey) {
  let updated = false
  if (!(project in CONFIG)) {
    CONFIG[project] = {}
  }

  if (!baseUrl) {
    baseUrl = CONFIG[project].base_url || ''
  }
  if (!baseUrl) {
    let domain = `${project}.djaoapp.com`
    const customDomain = await askQuestion(
        `Please enter the domain for project '${project}'\n` +
        `(default to: ${domain}): `)
    if (customDomain) {
      domain = customDomain
    }
    if (domain.match(/localhost/) || domain.match(/127.0.0.1/)) {
      baseUrl = `http://${domain}`
    } else {
      baseUrl = `https://${domain}`
    }
  }
  if (!CONFIG[project].base_url) {
    // eslint-disable-next-line dot-notation
    CONFIG[project]['base_url'] = baseUrl
    updated = true
  }

  if (!apiKey) {
    apiKey = CONFIG[project].api_key || ''
  }
  if (!apiKey) {
    apiKey = await askQuestion(
        `Please enter an API Key for ${baseUrl}\n` +
        '(see https://www.djaodjin.com/docs/faq/#api-keys for help): ')
  }
  if (!CONFIG[project].api_key) {
    CONFIG[project].api_key = apiKey
    updated = true
  }

  return { base_url: baseUrl, api_key: apiKey, updated }
}

async function getProjectConfig (projectName, baseUrl, apiKey) {
  const project = await getProject(projectName)
  const connect = await getProjectConnect(project.name, baseUrl, apiKey)

  return {
    name: project.name,
    base_url: connect.base_url,
    api_key: connect.api_key,
    updated: (project.updated || connect.updated)
  }
}

function saveConfig (config, configFilename) {
  if (!configFilename) {
    configFilename = CONFIG_FILENAME
  }
  if (!config) {
    config = CONFIG
  }
  if (!fs.existsSync(path.dirname(configFilename))) {
    fs.mkdirSync(path.dirname(configFilename))
  }
  fs.writeFileSync(configFilename, ini.stringify(config))
  console.log('saved configuration in', configFilename)
}

/** Uploads a new theme for a project.
 */
async function uploadTheme (args, baseUrl, apiKey, prefix) {
  async function zipdir (zipFilename, args, prefix) {
    const zip = new AdmZip()
    for (let idx = 0; idx < args.length; ++idx) {
      const arg = args[idx]
      zip.addLocalFolder(arg, prefix ? `${prefix}/${arg}` : arg)
    }
    zip.writeZip(zipFilename)
  }

  if (!args) {
    throw ValueError(
      'A single zip file or a list of directories must be present')
  }

  const src = args[0]
  let zipFilename = path.basename(path.resolve(src)) + '.zip'

  if (fs.existsSync(src) && fs.lstatSync(src).isFile()) {
    try {
      const zip = new AdmZip(src)
      zip.getEntries()
      if (args.length !== 1) {
        throw ValueError('You should specify a single zip file only.')
      }
      zipFilename = src
    } catch (err) {
    }
  } else if (fs.existsSync(src) && fs.lstatSync(src).isDirectory()) {
    if (prefix) {
      zipFilename = `${prefix}.zip`
    }
    await zipdir(zipFilename, args, prefix)
  } else {
    throw ValueError(`${args} is neither a single zip nor a list of directoies`)
  }
  const apiThemesURL = baseUrl + '/api/themes'
  const form = new FormData()
  const file = fs.readFileSync(zipFilename)
  form.append('file', file, path.basename(zipFilename))
  await axios.post(apiThemesURL, form, {
    auth: {
      username: `${apiKey}`,
      password: ''
    },
    headers: {
      ...form.getHeaders(),
      'Content-Length': form.getLengthSync()
    }
  }).then(function (resp) {
    const msg = JSON.stringify(resp.data)
    console.log(`POST ${apiThemesURL} returns ${resp.status} ${msg}`)
  }).catch(function (err) {
    const resp = err.response
    if (resp) {
      const msg = JSON.stringify(resp.data)
      console.log(`POST ${apiThemesURL} returns ${resp.status} ${msg}`)
    } else {
      // something happened that lead to an error.
      console.log('error:', err.message)
    }
  })
}

async function pubUpload (args) {
  const config = await getProjectConfig()
  if (config.updated) {
    saveConfig()
  }
  uploadTheme(args, config.base_url, config.api_key, config.name)
}

/** Main Entry point
 */
async function main (args) {
  console.log('read configuration from', CONFIG_FILENAME)
  if (fs.existsSync(CONFIG_FILENAME)) {
    CONFIG = ini.parse(fs.readFileSync(CONFIG_FILENAME, 'utf-8'))
  }
  await pubUpload(args)
  rdl.close()
}

try {
  main(process.argv.slice(2))
} catch (err) {
  console.log('error: ' + err)
  console.log('usage: ' + process.argv[0] + ' ' + process.argv[1] + ' files|dirs')
}
