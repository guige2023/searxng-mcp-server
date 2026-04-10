#!/usr/bin/env node

/**
 * SearXNG MCP Server - Stdio Wrapper
 * This wrapper allows the MCP to be used via stdio (for httpwrapper, Claude Desktop, etc.)
 * 
 * Features:
 * - Automatic configuration loading from ~/.searxng-mcp/.env
 * - Automatic Docker container management for SearXNG
 * - Python dependency auto-installation
 * - Cross-platform support (Windows/Mac/Linux)
 */

const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the directory where this script is located
const scriptDir = __dirname;
const serverPath = path.join(scriptDir, 'mcp_stdio_server.py');
const requirementsPath = path.join(scriptDir, 'requirements.txt');

// Environment loader (loads ~/.searxng-mcp/.env)
const { loadEnv, getBoolConfig, getConfig } = require('./env-loader.js');

// Docker manager
const dockerManager = require('./docker-manager.js');

// Find Python executable
function findPython() {
    // On Windows, prefer 'python' over 'python3'
    const pythonCommands = process.platform === 'win32' 
        ? ['python', 'python3'] 
        : ['python3', 'python'];

    for (const cmd of pythonCommands) {
        try {
            const result = spawnSync(cmd, ['--version'], {
                stdio: 'pipe',
                encoding: 'utf-8'
            });

            if (result.status === 0) {
                return cmd;
            }
        } catch (e) {
            // Continue to next command
        }
    }

    console.error('ERROR: Python is not installed or not in PATH');
    console.error('Please install Python 3.9 or newer');
    process.exit(1);
}

// Check and install Python dependencies if needed
function ensureDependencies(pythonCmd) {
    // Check if required Python deps are installed
    const checkResult = spawnSync(pythonCmd, ['-c', 'import sklearn, charset_normalizer'], {
        stdio: 'pipe',
        encoding: 'utf-8'
    });

    if (checkResult.status !== 0) {
        console.error('[Setup] Installing Python dependencies (first time only)...');
        
        const installResult = spawnSync(pythonCmd, [
            '-m', 'pip', 'install', '-r', requirementsPath, 
            '--quiet', '--disable-pip-version-check'
        ], {
            stdio: 'inherit'
        });

        if (installResult.status !== 0) {
            console.error('\n[Setup] WARNING: Failed to auto-install dependencies.');
            console.error(`Please manually run: ${pythonCmd} -m pip install -r ${requirementsPath}`);
            console.error('Continuing anyway (better_search tool may not work)...\n');
        } else {
            console.error('[Setup] Dependencies installed successfully!\n');
        }
    }
}

// Main async function
async function main() {
    // ========================================
    // Load Configuration from ~/.searxng-mcp/.env
    // ========================================
    console.error('[Config] Loading configuration...');
    loadEnv();
    
    // Log User Agent settings
    const uaRotation = getConfig('USER_AGENT_ROTATION', 'true');
    const uaStrategy = getConfig('USER_AGENT_STRATEGY', 'random');
    console.error(`[Config] User Agent Rotation: ${uaRotation}, Strategy: ${uaStrategy}`);

    // Check if server.py exists
    if (!fs.existsSync(serverPath)) {
        console.error(`ERROR: mcp_stdio_server.py not found at ${serverPath}`);
        process.exit(1);
    }

    // Get Python command
    const pythonCmd = findPython();

    // Ensure Python dependencies are installed
    ensureDependencies(pythonCmd);

    // ========================================
    // Docker Auto-Management
    // ========================================
    const skipDocker = process.env.SKIP_DOCKER === 'true';
    let searxngPort = parseInt(process.env.SEARXNG_PORT || '32768');

    if (!skipDocker) {
        console.error('[Docker] Checking SearXNG container...');
        
        const result = await dockerManager.ensureSearXNGRunning({
            port: searxngPort,
            containerName: process.env.SEARXNG_CONTAINER_NAME || 'searxng-mcp',
            autoPull: process.env.DOCKER_AUTO_PULL !== 'false'
        });

        if (!result.success) {
            console.error(`[Docker] ${result.message}`);
            
            // Provide helpful error message
            if (result.message.includes('not installed')) {
                console.error('\n========================================');
                console.error('Docker is required for SearXNG.');
                console.error('Install Docker Desktop: https://www.docker.com/products/docker-desktop');
                console.error('');
                console.error('Alternatively, set SKIP_DOCKER=true and run SearXNG manually:');
                console.error('  docker run -d --name searxng -p 32768:8080 searxng/searxng:latest');
                console.error('========================================\n');
            } else if (result.message.includes('not running')) {
                console.error('\n========================================');
                console.error('Docker daemon is not running.');
                console.error('Please start Docker Desktop and try again.');
                console.error('========================================\n');
            }
            
            process.exit(1);
        }

        // Update port if it was changed due to conflict
        if (result.port && result.port !== searxngPort) {
            console.error(`[Docker] Note: Using port ${result.port} instead of ${searxngPort}`);
            searxngPort = result.port;
        }

        console.error(`[Docker] ${result.message}`);

        // Setup cleanup handlers
        dockerManager.setupCleanupHandlers(
            process.env.SEARXNG_CONTAINER_NAME || 'searxng-mcp',
            process.env.STOP_ON_EXIT === 'true'
        );
    } else {
        console.error('[Docker] Skipped (SKIP_DOCKER=true)');
    }

    // ========================================
    // Start Python MCP Server
    // ========================================
    
    // Get environment variables from process.env or use defaults
    const env = {
        ...process.env,
        // Force UTF-8 IO for Python on Windows
        PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
        PYTHONUTF8: process.env.PYTHONUTF8 || '1',
        SEARXNG_BASE_URL: process.env.SEARXNG_BASE_URL || `http://localhost:${searxngPort}`,
        CONTENT_MAX_LENGTH: process.env.CONTENT_MAX_LENGTH || '10000',
        SEARCH_RESULT_LIMIT: process.env.SEARCH_RESULT_LIMIT || '10',
        DESIRED_TIMEZONE: process.env.DESIRED_TIMEZONE || 'UTC'
    };

    // Spawn Python process
    const pythonProcess = spawn(pythonCmd, [serverPath], {
        stdio: ['inherit', 'inherit', 'inherit'],
        env: env,
        cwd: scriptDir
    });

    // Handle process signals
    process.on('SIGINT', () => {
        pythonProcess.kill('SIGINT');
        process.exit(0);
    });

    process.on('SIGTERM', () => {
        pythonProcess.kill('SIGTERM');
        process.exit(0);
    });

    // Handle Python process exit
    pythonProcess.on('close', (code) => {
        process.exit(code || 0);
    });

    pythonProcess.on('error', (err) => {
        console.error('Failed to start Python process:', err);
        process.exit(1);
    });
}

// Run main function
main().catch(err => {
    console.error('Fatal error:', err.message);
    process.exit(1);
});
