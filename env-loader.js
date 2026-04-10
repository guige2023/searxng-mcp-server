/**
 * SearXNG MCP Server - Environment Loader
 * 
 * Loads configuration from ~/.searxng-mcp/.env file
 * Environment variables take precedence over .env file values
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// ========================================
// Configuration Paths
// ========================================
const CONFIG_DIR = path.join(os.homedir(), '.searxng-mcp');
const ENV_FILE = path.join(CONFIG_DIR, '.env');

/**
 * Load .env file from ~/.searxng-mcp/.env
 * Environment variables take precedence over .env file
 * 
 * @returns {boolean} true if .env file was loaded successfully
 */
function loadEnv() {
    if (!fs.existsSync(ENV_FILE)) {
        console.error('[Config] No .env file found at ~/.searxng-mcp/.env');
        console.error('[Config] Using default settings. Run "npm install" to generate .env file.');
        return false;
    }
    
    try {
        const envContent = fs.readFileSync(ENV_FILE, 'utf-8');
        let loadedCount = 0;
        
        envContent.split('\n').forEach(line => {
            line = line.trim();
            
            // Skip comments and empty lines
            if (!line || line.startsWith('#')) return;
            
            const equalIndex = line.indexOf('=');
            if (equalIndex === -1) return;
            
            const key = line.substring(0, equalIndex).trim();
            let value = line.substring(equalIndex + 1).trim();
            
            // Remove surrounding quotes if present
            if ((value.startsWith('"') && value.endsWith('"')) ||
                (value.startsWith("'") && value.endsWith("'"))) {
                value = value.slice(1, -1);
            }
            
            // Only set if not already set (environment variables take precedence)
            if (key && !process.env[key]) {
                process.env[key] = value;
                loadedCount++;
            }
        });
        
        console.error(`[Config] Loaded ${loadedCount} settings from ~/.searxng-mcp/.env`);
        return true;
        
    } catch (error) {
        console.error(`[Config] Error reading .env file: ${error.message}`);
        return false;
    }
}

/**
 * Get configuration value with fallback
 * @param {string} key - Environment variable name
 * @param {string} defaultValue - Default value if not set
 * @returns {string}
 */
function getConfig(key, defaultValue = '') {
    return process.env[key] || defaultValue;
}

/**
 * Get boolean configuration value
 * @param {string} key - Environment variable name
 * @param {boolean} defaultValue - Default value if not set
 * @returns {boolean}
 */
function getBoolConfig(key, defaultValue = false) {
    const value = (process.env[key] || '').toLowerCase();
    if (value === 'true' || value === '1' || value === 'yes') return true;
    if (value === 'false' || value === '0' || value === 'no') return false;
    return defaultValue;
}

/**
 * Get integer configuration value
 * @param {string} key - Environment variable name
 * @param {number} defaultValue - Default value if not set
 * @returns {number}
 */
function getIntConfig(key, defaultValue = 0) {
    const value = parseInt(process.env[key] || '');
    return isNaN(value) ? defaultValue : value;
}

/**
 * Get configuration directory path
 * @returns {string}
 */
function getConfigDir() {
    return CONFIG_DIR;
}

/**
 * Get .env file path
 * @returns {string}
 */
function getEnvFilePath() {
    return ENV_FILE;
}

// ========================================
// Auto-load .env on require
// ========================================
loadEnv();

module.exports = {
    loadEnv,
    getConfig,
    getBoolConfig,
    getIntConfig,
    getConfigDir,
    getEnvFilePath,
    CONFIG_DIR,
    ENV_FILE
};
