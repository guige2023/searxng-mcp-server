#!/usr/bin/env node

/**
 * SearXNG MCP Server - Post Install Script
 * 
 * This script runs after npm install and:
 * 1. Installs Python dependencies (requirements.txt)
 * 2. Creates ~/.searxng-mcp/ config directory
 * 3. Generates default .env file (only if not exists)
 * 4. Copies config edit scripts for user convenience
 */

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ========================================
// Configuration Paths
// ========================================
const CONFIG_DIR = path.join(os.homedir(), '.searxng-mcp');
const ENV_FILE = path.join(CONFIG_DIR, '.env');
const SCRIPTS_DIR = path.join(__dirname, 'scripts');

// ========================================
// Default .env Content
// ========================================
const DEFAULT_ENV_CONTENT = `# ==========================================
# SearXNG MCP Server - Configuration
# ==========================================
# Generated: ${new Date().toISOString()}
# 
# Edit this file to customize settings.
# Changes take effect on next server start (npx).
#
# Windows: %USERPROFILE%\\.searxng-mcp\\edit-config.bat
# Mac/Linux: ~/.searxng-mcp/edit-config.sh

# ==========================================
# Docker Settings
# ==========================================
SEARXNG_PORT=32768
SEARXNG_CONTAINER_NAME=searxng-mcp
DOCKER_AUTO_PULL=true
STOP_ON_EXIT=false

# ==========================================
# User Agent Settings (Bot Detection Bypass)
# ==========================================
# Rotate User-Agent to avoid 403 errors from sites like Wikipedia
USER_AGENT_ROTATION=true

# Strategy: random (default) or domain-sticky
# - random: Different UA for every request
# - domain-sticky: Same UA for same domain
USER_AGENT_STRATEGY=random

# Add custom User Agents (comma-separated, optional)
# CUSTOM_USER_AGENTS="Mozilla/5.0 ..., Mozilla/5.0 ..."

# ==========================================
# Rate Limiting
# ==========================================
RATE_LIMIT_RPM=300
RATE_LIMIT_TIMEOUT=60

# ==========================================
# Search Settings (SearXNG request parameters)
# ==========================================
# Language: ko, en, ja, auto, etc.
# SEARXNG_LANGUAGE=auto

# Safe Search: 0=off, 1=moderate, 2=strict
# SEARXNG_SAFE_SEARCH=0

# Time Range: day, week, month, year (empty = all time)
# SEARXNG_TIME_RANGE=

# Result limit per search
SEARXNG_RESULT_LIMIT=10

# ==========================================
# Content Crawling Settings
# ==========================================
CONTENT_MAX_LENGTH=10000
SEARCH_RESULT_LIMIT=10
`;

// ========================================
// Python Installation
// ========================================
function findPython() {
    const pythonCommands = process.platform === 'win32'
        ? ['python', 'python3', 'py']
        : ['python3', 'python'];

    for (const cmd of pythonCommands) {
        const args = cmd === 'py' ? ['-3', '--version'] : ['--version'];
        try {
            const result = spawnSync(cmd, args, { stdio: 'ignore' });
            if (result.status === 0) return cmd;
        } catch {
            // try next
        }
    }

    return null;
}

function runPipInstall(pythonCmd) {
    const requirementsPath = path.join(__dirname, 'requirements.txt');

    const pythonArgs = pythonCmd === 'py'
        ? ['-3', '-m', 'pip', 'install', '-r', requirementsPath, '--quiet', '--disable-pip-version-check']
        : ['-m', 'pip', 'install', '-r', requirementsPath, '--quiet', '--disable-pip-version-check'];

    const result = spawnSync(pythonCmd, pythonArgs, { stdio: 'inherit' });
    return result.status === 0;
}

// ========================================
// Config Setup
// ========================================
function setupConfigDirectory() {
    console.log('\n========================================');
    console.log('SearXNG MCP Server - Setup');
    console.log('========================================\n');

    // 1. Create config directory
    if (!fs.existsSync(CONFIG_DIR)) {
        try {
            fs.mkdirSync(CONFIG_DIR, { recursive: true });
            console.log(`[Setup] Created config directory: ${CONFIG_DIR}`);
        } catch (err) {
            console.error(`[Setup] Failed to create config directory: ${err.message}`);
            return false;
        }
    }

    // 2. Create .env file (only if not exists!)
    if (!fs.existsSync(ENV_FILE)) {
        try {
            fs.writeFileSync(ENV_FILE, DEFAULT_ENV_CONTENT, 'utf-8');
            console.log(`[Setup] Created default .env file: ${ENV_FILE}`);
            console.log('[Setup] You can edit settings anytime!');
        } catch (err) {
            console.error(`[Setup] Failed to create .env file: ${err.message}`);
            return false;
        }
    } else {
        console.log(`[Setup] Config file already exists: ${ENV_FILE}`);
        console.log('[Setup] Your existing settings are preserved.');
    }

    // 3. Copy edit scripts
    copyEditScripts();

    return true;
}

function copyEditScripts() {
    // Copy edit-config.bat (Windows)
    const batSource = path.join(SCRIPTS_DIR, 'edit-config.bat');
    const batDest = path.join(CONFIG_DIR, 'edit-config.bat');
    
    if (fs.existsSync(batSource)) {
        try {
            fs.copyFileSync(batSource, batDest);
            console.log('[Setup] Copied edit-config.bat');
        } catch (err) {
            // Non-critical error, continue
        }
    }

    // Copy edit-config.sh (Mac/Linux)
    const shSource = path.join(SCRIPTS_DIR, 'edit-config.sh');
    const shDest = path.join(CONFIG_DIR, 'edit-config.sh');
    
    if (fs.existsSync(shSource)) {
        try {
            fs.copyFileSync(shSource, shDest);
            // Make executable on Unix
            if (process.platform !== 'win32') {
                fs.chmodSync(shDest, '755');
            }
            console.log('[Setup] Copied edit-config.sh');
        } catch (err) {
            // Non-critical error, continue
        }
    }
}

// ========================================
// Main
// ========================================
(function main() {
    // Step 1: Setup config directory and .env
    const configOk = setupConfigDirectory();

    // Step 2: Install Python dependencies
    console.log('\n[Setup] Checking Python dependencies...');
    
    const pythonCmd = findPython();
    if (!pythonCmd) {
        console.warn('[Setup] Python not found; skipping requirements.txt install.');
        console.warn('[Setup] Install Python 3.9+ then run: python -m pip install -r requirements.txt');
    } else {
        const pipOk = runPipInstall(pythonCmd);
        if (!pipOk) {
            console.warn('[Setup] Failed to auto-install Python deps (continuing).');
            console.warn(`[Setup] Please run manually: ${pythonCmd} -m pip install -r requirements.txt`);
        } else {
            console.log('[Setup] Python dependencies installed successfully!');
        }
    }

    // Final message
    console.log('\n========================================');
    console.log('Setup Complete!');
    console.log('========================================');
    console.log('');
    console.log('To edit settings:');
    if (process.platform === 'win32') {
        console.log(`  ${path.join(CONFIG_DIR, 'edit-config.bat')}`);
        console.log('  or: notepad %USERPROFILE%\\.searxng-mcp\\.env');
    } else {
        console.log('  ~/.searxng-mcp/edit-config.sh');
        console.log('  or: nano ~/.searxng-mcp/.env');
    }
    console.log('');
    console.log('To run server:');
    console.log('  npx -y @otbossam/searxng-mcp-server');
    console.log('');

    process.exit(0);
})();
