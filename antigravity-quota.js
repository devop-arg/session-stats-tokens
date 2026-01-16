#!/usr/bin/env node

/**
 * Antigravity Quota Checker v3.0
 * Consulta quotas de todas las cuentas Antigravity configuradas
 * 
 * Características:
 * - Caché de access tokens con validación híbrida (tiempo + respuesta API)
 * - Caché de resultados de quotas (30 segundos)
 * - Auto-retry en caso de token inválido
 * - Modo compacto para integración con otros scripts
 * - Múltiples flags de control
 * 
 * Uso:
 *   node antigravity-quota.js [opciones]
 * 
 * Opciones:
 *   --compact    Salida compacta (sin caché local status)
 *   --refresh    Ignorar caché y forzar consulta a APIs
 *   --json       Salida en formato JSON
 *   --help       Mostrar ayuda
 */

const fs = require('fs').promises;
const fsSync = require('fs');
const https = require('https');
const path = require('path');
const os = require('os');

// ==================== CONFIGURACIÓN ====================

const CONFIG_DIR = path.join(os.homedir(), '.config', 'opencode');
const ACCOUNTS_PATH = path.join(CONFIG_DIR, 'antigravity-accounts.json');
const TOKENS_CACHE_PATH = path.join(CONFIG_DIR, 'antigravity-tokens.json');
const QUOTA_CACHE_PATH = path.join(CONFIG_DIR, 'antigravity-quota-cache.json');
const SESSION_HISTORY_PATH = path.join(os.homedir(), 'scripts', 'session-stats', 'session_history.json');

const DELAY_MS = 1000; // 1 segundo entre cuentas
const TIMEOUT_MS = 10000; // 10 segundos timeout
const TOKEN_EXPIRY_BUFFER = 60000; // 1 minuto de buffer antes de expiración
const QUOTA_CACHE_TTL = 30000; // 30 segundos de caché para quotas
const RECENT_ACTIVITY_WINDOW_MS = 60 * 60 * 1000; // 60 minutos
const WINDOW_ACTIVE_THRESHOLD_MS = 6 * 60 * 60 * 1000; // 6 horas

// Constantes de la API
const GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token';
const CLOUDCODE_BASE_URL = 'https://cloudcode-pa.googleapis.com';
const ANTIGRAVITY_CLIENT_ID = 'REDACTED';
const ANTIGRAVITY_CLIENT_SECRET = 'REDACTED';

const CLOUDCODE_METADATA = {
  ideType: 'ANTIGRAVITY',
  platform: 'PLATFORM_UNSPECIFIED',
  pluginType: 'GEMINI',
};

// ==================== PARSEO DE ARGUMENTOS ====================

const args = process.argv.slice(2);
const FLAGS = {
  compact: args.includes('--compact') || args.includes('-c'),
  refresh: args.includes('--refresh') || args.includes('-r'),
  json: args.includes('--json') || args.includes('-j'),
  help: args.includes('--help') || args.includes('-h'),
};

if (FLAGS.help) {
  console.log(`
Antigravity Quota Checker v3.0

Uso: node antigravity-quota.js [opciones]

Opciones:
  --compact, -c    Salida compacta (sin detalles de caché local)
  --refresh, -r    Ignorar caché y forzar consulta a APIs
  --json, -j       Salida en formato JSON
  --help, -h       Mostrar esta ayuda

Ejemplos:
  node antigravity-quota.js              # Uso normal con caché
  node antigravity-quota.js --compact    # Salida compacta
  node antigravity-quota.js --refresh    # Forzar actualización
  node antigravity-quota.js --json       # Output JSON
`);
  process.exit(0);
}

// ==================== CACHÉ DE TOKENS ====================

let tokenCache = null;

async function loadTokenCache() {
  try {
    if (!fsSync.existsSync(TOKENS_CACHE_PATH)) {
      return { tokens: {} };
    }
    const content = await fs.readFile(TOKENS_CACHE_PATH, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    return { tokens: {} };
  }
}

async function saveTokenCache(cache) {
  try {
    await fs.writeFile(TOKENS_CACHE_PATH, JSON.stringify(cache, null, 2), 'utf-8');
  } catch (error) {
    // Silencioso
  }
}

function isTokenExpiredByTime(tokenData) {
  if (!tokenData || !tokenData.access_token || !tokenData.expires_at) {
    return true;
  }
  const now = Date.now();
  return (tokenData.expires_at - now) <= TOKEN_EXPIRY_BUFFER;
}

async function getCachedToken(email) {
  if (!tokenCache) {
    tokenCache = await loadTokenCache();
  }
  
  const cached = tokenCache.tokens[email];
  
  if (cached && !isTokenExpiredByTime(cached)) {
    const remainingTime = Math.floor((cached.expires_at - Date.now()) / 1000 / 60);
    return {
      token: cached.access_token,
      fromCache: true,
      expiresIn: remainingTime,
    };
  }
  
  return null;
}

async function cacheToken(email, accessToken, expiresIn) {
  if (!tokenCache) {
    tokenCache = await loadTokenCache();
  }
  
  const expiresAt = Date.now() + (expiresIn * 1000);
  
  tokenCache.tokens[email] = {
    access_token: accessToken,
    expires_at: expiresAt,
  };
  
  await saveTokenCache(tokenCache);
}

async function invalidateToken(email) {
  if (!tokenCache) {
    tokenCache = await loadTokenCache();
  }
  
  if (tokenCache.tokens[email]) {
    delete tokenCache.tokens[email];
    await saveTokenCache(tokenCache);
  }
}

// ==================== CACHÉ DE QUOTAS ====================

async function loadQuotaCache() {
  try {
    if (!fsSync.existsSync(QUOTA_CACHE_PATH)) {
      return null;
    }
    const content = await fs.readFile(QUOTA_CACHE_PATH, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    return null;
  }
}

async function saveQuotaCache(results) {
  try {
    const cache = {
      timestamp: Date.now(),
      ttl_seconds: QUOTA_CACHE_TTL / 1000,
      results: results,
    };
    await fs.writeFile(QUOTA_CACHE_PATH, JSON.stringify(cache, null, 2), 'utf-8');
  } catch (error) {
    // Silencioso
  }
}

function isQuotaCacheValid(cache) {
  if (!cache || !cache.timestamp) {
    return false;
  }
  const age = Date.now() - cache.timestamp;
  return age < QUOTA_CACHE_TTL;
}

// ==================== UTILIDADES ====================

function isAccountExhausted(result) {
  if (!result || !result.models) return false;
  return result.models.some(m => m.remainingPercentage <= 0);
}

function formatDuration(ms) {
  const absMs = Math.abs(ms);
  const seconds = Math.floor(absMs / 1000);
  const d = Math.floor(seconds / (24 * 3600));
  const h = Math.floor((seconds % (24 * 3600)) / 3600);
  const m = Math.floor((seconds % 3600) / 60);

  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function shortEmail(email) {
  return email.split('@')[0];
}

function progressBar(percent) {
  const width = 10;
  const filled = Math.round((percent / 100) * width);
  const empty = width - filled;
  
  const bar = '█'.repeat(filled) + '░'.repeat(empty);
  return `[${bar}] ${percent.toFixed(0).padStart(3)}%`;
}

function extractProjectId(project) {
  if (typeof project === 'string' && project) return project;
  if (project && typeof project === 'object' && 'id' in project) {
    const id = project.id;
    if (id) return id;
  }
  return undefined;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function parseSessionDate(dateString) {
  if (!dateString) return null;
  const parsed = new Date(dateString);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

async function loadSessionHistory() {
  try {
    if (!fsSync.existsSync(SESSION_HISTORY_PATH)) {
      return {};
    }
    const content = await fs.readFile(SESSION_HISTORY_PATH, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    return {};
  }
}

function getRecentActivityByEmail(history, config, sinceMs) {
  const activity = {};
  const emailByIndex = config.accounts.map(account => account.email);

  Object.values(history).forEach((session) => {
    const sessionDate = parseSessionDate(session?.date);
    if (!sessionDate) return;
    if (sessionDate.getTime() < sinceMs) return;

    Object.keys(session?.by_model || {}).forEach((modelKey) => {
      if (!modelKey.startsWith('antigravity-')) return;
      const stripped = modelKey.replace('antigravity-', '');

      if (stripped.includes('gemini') && config.activeIndexByFamily?.gemini != null) {
        const email = emailByIndex[config.activeIndexByFamily.gemini];
        if (email) activity[email] = true;
      }

      if (stripped.includes('claude') && config.activeIndexByFamily?.claude != null) {
        const email = emailByIndex[config.activeIndexByFamily.claude];
        if (email) activity[email] = true;
      }
    });
  });

  return activity;
}

function isWindowActive(result) {
  if (!result?.models?.length) return false;
  return result.models.some((model) => model.timeUntilReset > 0 && model.timeUntilReset < WINDOW_ACTIVE_THRESHOLD_MS);
}

// ==================== HTTP HELPERS ====================

function httpsRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    
    const reqOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port || 443,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: options.headers || {},
      timeout: TIMEOUT_MS,
    };

    const req = https.request(reqOptions, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve({ data: JSON.parse(data), status: res.statusCode });
          } catch (e) {
            resolve({ data: data, status: res.statusCode });
          }
        } else {
          reject(new Error(`HTTP_${res.statusCode}`));
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('TIMEOUT'));
    });

    if (options.body) {
      req.write(options.body);
    }

    req.end();
  });
}

// ==================== API FUNCTIONS ====================

async function generateNewToken(refreshToken) {
  const params = new URLSearchParams({
    client_id: ANTIGRAVITY_CLIENT_ID,
    client_secret: ANTIGRAVITY_CLIENT_SECRET,
    refresh_token: refreshToken,
    grant_type: 'refresh_token',
  });

  const response = await httpsRequest(GOOGLE_TOKEN_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: params.toString(),
  });

  return {
    accessToken: response.data.access_token,
    expiresIn: response.data.expires_in,
  };
}

async function getAccessToken(email, refreshToken, forceNew = false) {
  // Si no forzamos nuevo, intentar usar caché
  if (!forceNew) {
    const cached = await getCachedToken(email);
    if (cached) {
      return {
        accessToken: cached.token,
        fromCache: true,
        expiresIn: cached.expiresIn,
      };
    }
  }

  // Generar nuevo token
  const newToken = await generateNewToken(refreshToken);
  
  // Cachear el nuevo token
  await cacheToken(email, newToken.accessToken, newToken.expiresIn);

  return {
    accessToken: newToken.accessToken,
    fromCache: false,
    expiresIn: Math.floor(newToken.expiresIn / 60),
  };
}

async function fetchAvailableModels(accessToken, projectId) {
  const payload = projectId ? { project: projectId } : {};
  
  const response = await httpsRequest(
    `${CLOUDCODE_BASE_URL}/v1internal:fetchAvailableModels`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'User-Agent': 'antigravity',
      },
      body: JSON.stringify(payload),
    }
  );

  return response.data;
}

// ==================== MAIN FUNCTIONS ====================

async function fetchAllAccounts(accounts, verbose = true) {
  const results = [];
  for (let i = 0; i < accounts.length; i++) {
    const account = accounts[i];
    if (verbose) {
      console.log(`[${i + 1}/${accounts.length}] ${shortEmail(account.email)}`);
    }
    if (i > 0) {
      await delay(DELAY_MS);
    }
    results.push(await fetchAccountQuota(account, verbose));
  }
  return results;
}

async function fetchAccountQuota(account, verbose = true) {
  const log = verbose ? console.log.bind(console) : () => {};
  const write = verbose ? process.stdout.write.bind(process.stdout) : () => {};
  
  try {
    // 1. Obtener access token (primero intentar desde caché)
    write('   ⏳ Token...');
    let tokenResult = await getAccessToken(account.email, account.refreshToken);
    
    if (tokenResult.fromCache) {
      log(` ✓ cache (${tokenResult.expiresIn}m)`);
    } else {
      log(` ✓ nuevo (${tokenResult.expiresIn}m)`);
    }

    let accessToken = tokenResult.accessToken;
    let projectId = account.projectId || account.managedProjectId;

    // 2. Consultar modelos (con retry si token inválido)
    write('   ⏳ Quotas...');
    
    let quotaResponse;
    try {
      quotaResponse = await fetchAvailableModels(accessToken, projectId);
    } catch (error) {
      // Si es error 401/403, el token está inválido - generar nuevo y reintentar
      if (error.message.includes('401') || error.message.includes('403')) {
        log(' ⚠ token inválido, regenerando...');
        await invalidateToken(account.email);
        
        write('   ⏳ Retry...');
        tokenResult = await getAccessToken(account.email, account.refreshToken, true);
        accessToken = tokenResult.accessToken;
        log(` ✓ nuevo token`);
        
        write('   ⏳ Quotas...');
        quotaResponse = await fetchAvailableModels(accessToken, projectId);
      } else {
        throw error;
      }
    }
    
    if (!quotaResponse.models) {
      log(' ⚠ sin modelos');
      return { email: account.email, success: true, models: [] };
    }

    // 3. Procesar modelos
    const now = Date.now();
    const models = [];

    for (const [modelKey, info] of Object.entries(quotaResponse.models)) {
      const quotaInfo = info.quotaInfo;
      if (!quotaInfo) continue;

      const label = info.displayName || modelKey;
      const lowerLabel = label.toLowerCase();
      
      // Filtrar modelos irrelevantes
      if (lowerLabel.startsWith('chat_') || 
          lowerLabel.startsWith('rev19') || 
          lowerLabel.includes('gemini 2.5') || 
          lowerLabel.includes('gemini 3 pro image')) {
        continue;
      }

      const remainingFraction = Math.min(1, Math.max(0, quotaInfo.remainingFraction ?? 0));
      
      let resetTime;
      if (quotaInfo.resetTime) {
        const parsed = new Date(quotaInfo.resetTime);
        resetTime = Number.isNaN(parsed.getTime()) ? new Date(now + 86400000) : parsed;
      } else {
        resetTime = new Date(now + 86400000);
      }

      const timeUntilReset = Math.max(0, resetTime.getTime() - now);

      models.push({
        label,
        modelId: info.model || modelKey,
        remainingPercentage: remainingFraction * 100,
        isExhausted: remainingFraction <= 0,
        timeUntilReset,
        timeUntilResetFormatted: formatDuration(timeUntilReset),
      });
    }

    models.sort((a, b) => a.label.localeCompare(b.label));
    log(` ✓ ${models.length} modelos`);

    return {
      email: account.email,
      success: true,
      models,
    };

  } catch (error) {
    log(` ✗ ${error.message}`);
    return {
      email: account.email,
      success: false,
      error: error.message,
    };
  }
}

function getLocalRateLimitInfo(data) {
  const now = Date.now();
  let output = '';

  const categories = {
    'Antigravity': [],
    'Gemini CLI': [],
  };

  const allModels = new Set();
  data.accounts.forEach((acc) => {
    if (acc.rateLimitResetTimes) {
      Object.keys(acc.rateLimitResetTimes).forEach((k) => allModels.add(k));
    }
  });

  Array.from(allModels).forEach((model) => {
    if (model.startsWith('gemini-antigravity:') || model.includes('claude')) {
      categories['Antigravity'].push(model);
    } else if (model.startsWith('gemini-cli:')) {
      categories['Gemini CLI'].push(model);
    }
  });

  for (const [category, models] of Object.entries(categories)) {
    if (models.length === 0) continue;

    output += `\n### ${category}\n`;

    for (const model of models.sort()) {
      const cleanName = model.split(':').pop() || model;
      output += `#### ${cleanName}\n`;
      output += 'STATUS   RESET TIME       LAST USED        ACCOUNT\n';
      
      const accountStatuses = data.accounts
        .map((acc) => {
          const resetTime = acc.rateLimitResetTimes?.[model] || 0;
          const remaining = resetTime - now;
          const available = resetTime === 0 || remaining <= 0;
          
          let statusText = available ? 'READY' : 'WAIT';
          let resetTimeStr;
          let lastUsedStr;

          if (resetTime === 0) {
            resetTimeStr = '-';
            lastUsedStr = 'Never used';
          } else if (available) {
            resetTimeStr = 'Ready';
            lastUsedStr = `${formatDuration(Math.abs(remaining))} ago`;
          } else {
            resetTimeStr = formatDuration(remaining);
            lastUsedStr = '-';
          }

          return { 
            email: shortEmail(acc.email), 
            remaining, 
            statusText, 
            resetTimeStr, 
            lastUsedStr 
          };
        })
        .sort((a, b) => a.remaining - b.remaining);

      for (const acc of accountStatuses) {
        const status = acc.statusText.padEnd(9, ' ');
        const reset = acc.resetTimeStr.padEnd(17, ' ');
        const last = acc.lastUsedStr.padEnd(17, ' ');
        const email = acc.email;
        output += `${status}${reset}${last}${email}\n`;
      }
      output += '\n';
    }
  }

  return output;
}

function formatResults(results, config, cacheInfo) {
  let output = '';
  const checkType = cacheInfo.checkType || (cacheInfo.fromCache ? 'cache' : 'full');
  const activeEmail = cacheInfo.activeEmail;
  const recentActivity = cacheInfo.recentActivity || {};
  const windowActiveEmails = cacheInfo.windowActiveEmails || new Set();
  
  // Header con info de check
  if (checkType === 'cache') {
    const ageSeconds = Math.floor((Date.now() - cacheInfo.timestamp) / 1000);
    output += `☁️  QUOTAS (cache ${ageSeconds}s)\n`;
  } else if (checkType === 'smart') {
    output += `☁️  QUOTAS (smart: ${shortEmail(activeEmail)})\n`;
  } else {
    output += `☁️  QUOTAS (full sweep)\n`;
  }

  const errors = [];
  const allApiModels = new Map();

  for (const result of results) {
    if (!result.success || !result.models) {
      errors.push(`${shortEmail(result.email)}: ${result.error || 'error'}`);
      continue;
    }

    for (const model of result.models) {
      if (!allApiModels.has(model.modelId)) {
        allApiModels.set(model.modelId, { label: model.label, accounts: [] });
      }
      allApiModels.get(model.modelId).accounts.push({
        email: result.email,
        percentage: model.remainingPercentage,
        resetIn: model.timeUntilResetFormatted,
        isExhausted: model.isExhausted,
        recentActivity: Boolean(recentActivity[result.email]),
        windowActive: windowActiveEmails.has(result.email),
      });
    }
  }

  if (errors.length > 0) {
    output += `⚠️  Errores: ${errors.join(', ')}\n`;
  }

  // Agrupar modelos con misma quota
  const sortedModels = Array.from(allApiModels.entries()).sort((a, b) =>
    a[1].label.localeCompare(b[1].label)
  );

  const modelGroups = new Map();

  for (const [modelId, modelData] of sortedModels) {
    const signature = modelData.accounts
      .map(a => `${a.email}:${a.percentage.toFixed(1)}:${a.resetIn}`)
      .sort()
      .join('|');

    if (modelGroups.has(signature)) {
      modelGroups.get(signature).labels.push(modelData.label);
    } else {
      modelGroups.set(signature, { labels: [modelData.label], accounts: modelData.accounts });
    }
  }

  // Mostrar grupos
  for (const [signature, group] of modelGroups) {
    const title = group.labels.join(' / ');
    output += `\n### ${title}\n`;
    
    const sorted = group.accounts.sort((a, b) => b.percentage - a.percentage);
    
    for (const acc of sorted) {
      const bar = progressBar(acc.percentage);
      const reset = acc.resetIn.padEnd(10);
      const email = shortEmail(acc.email);
      const tags = [];
      if (acc.recentActivity) tags.push('actividad reciente');
      if (!acc.recentActivity && acc.windowActive) tags.push('ventana activa');
      const tagText = tags.length ? ` (${tags.join(', ')})` : '';
      output += `${bar}  ${reset}  ${email}${tagText}\n`;
    }
  }

  // Local cache (solo si no es modo compacto)
  if (!FLAGS.compact) {
    output += '\n────────────────────────────────────────\n';
    output += '\n💾 LOCAL CACHE\n';
    output += getLocalRateLimitInfo(config);
  }

  return output;
}

async function main() {
  // 1. Leer configuración
  let config;
  try {
    const content = await fs.readFile(ACCOUNTS_PATH, 'utf-8');
    config = JSON.parse(content);
  } catch (error) {
    console.error(`✗ Error: No se pudo leer ${ACCOUNTS_PATH}`);
    process.exit(1);
  }

  const activeIndex = config.activeIndex ?? 0;
  const activeAccount = config.accounts[activeIndex];
  
  // 2. Leer actividad reciente
  const sessionHistory = await loadSessionHistory();
  const recentActivity = getRecentActivityByEmail(
    sessionHistory,
    config,
    Date.now() - RECENT_ACTIVITY_WINDOW_MS
  );

  // 3. Verificar caché de quotas
  let results;
  let cache = await loadQuotaCache();
  let checkType = 'full';
  let timestamp = Date.now();

  if (!FLAGS.refresh && cache) {
    if (isQuotaCacheValid(cache)) {
      // Usar caché total
      checkType = 'cache';
      results = cache.results;
      timestamp = cache.timestamp;
    } else {
      // Caché expirado -> ¿Smart Check o Full Sweep?
      const prevActive = cache.results?.find(r => r.email === activeAccount.email);
      const isExhausted = isAccountExhausted(prevActive);
      
      if (isExhausted || recentActivity[activeAccount.email]) {
        // Agotada o con actividad -> Full Sweep
        checkType = 'full';
      } else {
        // OK -> Smart Check (solo la activa)
        checkType = 'smart';
      }
    }
  }

  // 3. Ejecutar consultas si es necesario
  if (checkType === 'full') {
    if (!FLAGS.json) {
      console.log(`🔄 Full Sweep: Consultando todas las cuentas...\n`);
    }
    results = await fetchAllAccounts(config.accounts, !FLAGS.json);
    timestamp = Date.now();
    await saveQuotaCache(results);
  } else if (checkType === 'smart') {
    if (!FLAGS.json) {
      console.log(`🚀 Smart Check: Actualizando ${shortEmail(activeAccount.email)}...\n`);
    }
    const activeResult = await fetchAccountQuota(activeAccount, !FLAGS.json);
    
    // Combinar: dato fresco de la activa + caché de las otras
    results = cache.results.map(r => 
      r.email === activeAccount.email ? activeResult : r
    );
    timestamp = Date.now();
    await saveQuotaCache(results);
    
    if (!FLAGS.json) console.log('');
  }

  // 4. Formatear y mostrar resultados
  const windowActiveEmails = new Set(
    results
      .filter(result => isWindowActive(result))
      .map(result => result.email)
  );

  const cacheInfo = { 
    checkType, 
    timestamp, 
    fromCache: checkType === 'cache',
    activeEmail: activeAccount.email,
    recentActivity,
    windowActiveEmails,
  };

  if (FLAGS.json) {
    console.log(JSON.stringify({
      timestamp,
      checkType,
      results,
    }, null, 2));
  } else {
    console.log(formatResults(results, config, cacheInfo));
  }
}

// Ejecutar
main().catch((error) => {
  console.error(`✗ Error fatal: ${error.message}`);
  process.exit(1);
});
