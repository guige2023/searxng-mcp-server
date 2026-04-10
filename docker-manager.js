/**
 * Docker Manager for SearXNG Container
 * Automatically manages SearXNG container lifecycle for seamless npx usage
 */

const { execSync, spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Cache file path
const CACHE_FILE = path.join(os.homedir(), '.searxng-mcp-cache.json');

// Default configuration
const DEFAULT_CONFIG = {
    containerName: process.env.SEARXNG_CONTAINER_NAME || 'searxng-mcp',
    port: parseInt(process.env.SEARXNG_PORT || '32768'),
    image: process.env.SEARXNG_IMAGE || 'searxng/searxng:latest',
    autoPull: process.env.DOCKER_AUTO_PULL !== 'false',
    stopOnExit: process.env.STOP_ON_EXIT === 'true',
    healthCheckTimeout: parseInt(process.env.HEALTH_CHECK_TIMEOUT || '60000'), // 60 seconds
    healthCheckInterval: 1000 // 1 second
};

// ========================================
// Cache Management
// ========================================

/**
 * Read cache from file
 */
function readCache() {
    try {
        if (fs.existsSync(CACHE_FILE)) {
            const data = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf-8'));
            return data;
        }
    } catch (e) {
        // Cache corrupted, ignore
    }
    return null;
}

/**
 * Write cache to file
 */
function writeCache(data) {
    try {
        fs.writeFileSync(CACHE_FILE, JSON.stringify({
            ...data,
            timestamp: Date.now()
        }, null, 2));
    } catch (e) {
        // Ignore write errors
    }
}

/**
 * Check if cache exists
 */
function isCacheValid(cache) {
    // Permanent cache - just check if it exists and has port
    return cache && cache.port;
}

/**
 * Quick HTTP health check (fast, ~100ms)
 */
async function quickHealthCheck(port) {
    return new Promise((resolve) => {
        const req = http.get(`http://localhost:${port}/`, (res) => {
            resolve(res.statusCode === 200);
        });
        req.on('error', () => resolve(false));
        req.setTimeout(500, () => {  // 500ms timeout for quick check
            req.destroy();
            resolve(false);
        });
    });
}

/**
 * Check if Docker is installed and running
 */
function checkDockerInstalled() {
    try {
        execSync('docker --version', { stdio: 'pipe' });
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Check if Docker daemon is running
 */
function checkDockerRunning() {
    try {
        execSync('docker info', { stdio: 'pipe' });
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Get container status
 * @returns {'running' | 'stopped' | 'not_found'}
 */
function getContainerStatus(containerName) {
    try {
        const result = execSync(
            `docker ps -a --filter name=^${containerName}$ --format "{{.State}}"`,
            { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
        ).trim();

        if (!result) return 'not_found';
        if (result === 'running') return 'running';
        return 'stopped';
    } catch (e) {
        return 'not_found';
    }
}

/**
 * Find any running SearXNG container
 * Checks common container names: searxng, searxng-mcp, searxng-docker
 * @returns {{ name: string, port: number } | null}
 */
function findExistingSearXNGContainer() {
    const commonNames = ['searxng', 'searxng-mcp', 'searxng-docker', 'searxng-local'];
    
    for (const name of commonNames) {
        try {
            // Check if container exists and is running
            const stateResult = execSync(
                `docker ps --filter name=^${name}$ --format "{{.State}}"`,
                { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
            ).trim();
            
            if (stateResult === 'running') {
                // Get the port mapping
                const portResult = execSync(
                    `docker port ${name} 8080`,
                    { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
                ).trim();
                
                // Parse port from "0.0.0.0:32768" or ":::32768"
                const portMatch = portResult.match(/:(\d+)$/);
                if (portMatch) {
                    const port = parseInt(portMatch[1]);
                    console.error(`[Docker] Found existing SearXNG container: ${name} on port ${port}`);
                    return { name, port };
                }
            }
        } catch (e) {
            // Container doesn't exist or error, continue checking
        }
    }
    
    return null;
}

/**
 * Check if port is already in use
 */
function isPortInUse(port) {
    try {
        // Try to detect if port is in use
        if (process.platform === 'win32') {
            const result = execSync(`netstat -ano | findstr :${port}`, { 
                encoding: 'utf-8', 
                stdio: ['pipe', 'pipe', 'pipe'] 
            });
            return result.trim().length > 0;
        } else {
            const result = execSync(`lsof -i :${port}`, { 
                encoding: 'utf-8', 
                stdio: ['pipe', 'pipe', 'pipe'] 
            });
            return result.trim().length > 0;
        }
    } catch (e) {
        // Command failed = port not in use
        return false;
    }
}

/**
 * Check if the process on the port is SearXNG
 */
async function isSearXNGOnPort(port) {
    return new Promise((resolve) => {
        const req = http.get(`http://localhost:${port}/`, (res) => {
            // SearXNG returns HTML page
            resolve(res.statusCode === 200);
        });
        req.on('error', () => resolve(false));
        req.setTimeout(3000, () => {
            req.destroy();
            resolve(false);
        });
    });
}

/**
 * Wait for SearXNG to be healthy
 */
async function waitForHealthy(port, timeout = 60000) {
    const startTime = Date.now();
    const interval = 1000;

    console.error(`[Docker] Waiting for SearXNG to be ready on port ${port}...`);

    while (Date.now() - startTime < timeout) {
        try {
            const isReady = await new Promise((resolve) => {
                const req = http.get(`http://localhost:${port}/`, (res) => {
                    resolve(res.statusCode === 200);
                });
                req.on('error', () => resolve(false));
                req.setTimeout(2000, () => {
                    req.destroy();
                    resolve(false);
                });
            });

            if (isReady) {
                console.error(`[Docker] SearXNG is ready!`);
                return true;
            }
        } catch (e) {
            // Ignore and retry
        }

        await new Promise(r => setTimeout(r, interval));
    }

    console.error(`[Docker] Timeout waiting for SearXNG (${timeout}ms)`);
    return false;
}

/**
 * Pull the latest SearXNG image
 */
function pullImage(image) {
    console.error(`[Docker] Pulling image: ${image}...`);
    try {
        execSync(`docker pull ${image}`, { stdio: 'inherit' });
        console.error(`[Docker] Image pulled successfully`);
        return true;
    } catch (e) {
        console.error(`[Docker] Failed to pull image: ${e.message}`);
        return false;
    }
}

/**
 * Check if image exists locally
 */
function hasLocalImage(image) {
    try {
        const result = execSync(
            `docker images -q ${image}`,
            { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
        ).trim();
        return result.length > 0;
    } catch (e) {
        return false;
    }
}

/**
 * Start existing container
 */
function startContainer(containerName) {
    console.error(`[Docker] Starting existing container: ${containerName}`);
    try {
        execSync(`docker start ${containerName}`, { stdio: 'pipe' });
        return true;
    } catch (e) {
        console.error(`[Docker] Failed to start container: ${e.message}`);
        return false;
    }
}

/**
 * Get the path to the bundled settings.yml file
 */
function getSettingsPath() {
    // Settings file is bundled with the package
    const bundledSettings = path.join(__dirname, 'settings.yml');
    if (fs.existsSync(bundledSettings)) {
        return bundledSettings;
    }
    return null;
}

/**
 * Ensure config directory exists and copy settings
 * Returns the config directory path for volume mount
 */
function ensureConfigDirectory() {
    const configDir = path.join(os.homedir(), '.searxng-mcp-config');
    const settingsFile = path.join(configDir, 'settings.yml');
    
    // Create config directory if it doesn't exist
    if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
        console.error(`[Docker] Created config directory: ${configDir}`);
    }
    
    // Copy bundled settings.yml if not exists or if bundled is newer
    const bundledSettings = getSettingsPath();
    if (bundledSettings) {
        const shouldCopy = !fs.existsSync(settingsFile);
        if (shouldCopy) {
            fs.copyFileSync(bundledSettings, settingsFile);
            console.error(`[Docker] Copied default settings.yml to ${configDir}`);
        }
    }
    
    return configDir;
}

/**
 * Create and run a new container
 */
function createContainer(config) {
    const { containerName, port, image } = config;
    
    console.error(`[Docker] Creating new container: ${containerName}`);
    console.error(`[Docker] Port: ${port}, Image: ${image}`);

    try {
        // Ensure config directory with settings.yml exists
        const configDir = ensureConfigDirectory();
        
        // Convert Windows path to Docker-compatible path
        let dockerConfigPath = configDir;
        if (process.platform === 'win32') {
            // Convert C:\Users\... to /c/Users/... for Docker
            dockerConfigPath = configDir.replace(/\\/g, '/').replace(/^([A-Za-z]):/, (_, letter) => `/${letter.toLowerCase()}`);
        }
        
        console.error(`[Docker] Mounting config: ${dockerConfigPath}:/etc/searxng`);
        
        const cmd = [
            'docker run -d',
            `--name ${containerName}`,
            `-p ${port}:8080`,
            `-v "${dockerConfigPath}:/etc/searxng"`,
            '--restart unless-stopped',
            image
        ].join(' ');

        execSync(cmd, { stdio: 'pipe' });
        console.error(`[Docker] Container created successfully`);
        return true;
    } catch (e) {
        console.error(`[Docker] Failed to create container: ${e.message}`);
        return false;
    }
}

/**
 * Stop container
 */
function stopContainer(containerName) {
    console.error(`[Docker] Stopping container: ${containerName}`);
    try {
        execSync(`docker stop ${containerName}`, { stdio: 'pipe' });
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Find available port starting from the default
 */
function findAvailablePort(startPort) {
    let port = startPort;
    const maxAttempts = 10;

    for (let i = 0; i < maxAttempts; i++) {
        if (!isPortInUse(port)) {
            return port;
        }
        port++;
    }

    return null;
}

/**
 * Main function: Ensure SearXNG is running
 * @returns {Promise<{success: boolean, port: number, message: string}>}
 */
async function ensureSearXNGRunning(options = {}) {
    const config = { ...DEFAULT_CONFIG, ...options };
    
    // ========================================
    // Fast Path: Check cache first
    // ========================================
    const cache = readCache();
    if (isCacheValid(cache) && cache.port) {
        // Quick health check on cached port
        const isHealthy = await quickHealthCheck(cache.port);
        if (isHealthy) {
            console.error(`[Docker] SearXNG ready on port ${cache.port} (cached)`);
            return {
                success: true,
                port: cache.port,
                message: `Using cached SearXNG on port ${cache.port}`
            };
        }
        // Cache invalid, continue with full check
        console.error(`[Docker] Cache expired or unhealthy, running full check...`);
    }

    // ========================================
    // Full Check Path
    // ========================================
    
    // Step 1: Check Docker installation
    if (!checkDockerInstalled()) {
        return {
            success: false,
            port: null,
            message: 'Docker is not installed. Please install Docker Desktop: https://www.docker.com/products/docker-desktop'
        };
    }

    // Step 2: Check Docker daemon
    if (!checkDockerRunning()) {
        return {
            success: false,
            port: null,
            message: 'Docker daemon is not running. Please start Docker Desktop.'
        };
    }

    // Step 3: Check if any SearXNG container is already running (searxng, searxng-mcp, etc.)
    const existingContainer = findExistingSearXNGContainer();
    if (existingContainer) {
        console.error(`[Docker] Reusing existing container: ${existingContainer.name}`);
        const healthy = await waitForHealthy(existingContainer.port, 5000); // Quick check
        if (healthy) {
            // Save to cache
            writeCache({ port: existingContainer.port, containerName: existingContainer.name });
            return {
                success: true,
                port: existingContainer.port,
                message: `Using existing SearXNG container "${existingContainer.name}" on port ${existingContainer.port}`
            };
        }
    }

    // Step 4: Check if port is already in use by SearXNG (non-docker)
    if (isPortInUse(config.port)) {
        const isSearXNG = await isSearXNGOnPort(config.port);
        if (isSearXNG) {
            console.error(`[Docker] SearXNG already running on port ${config.port}`);
            // Save to cache
            writeCache({ port: config.port, containerName: null });
            return {
                success: true,
                port: config.port,
                message: `Using existing SearXNG on port ${config.port}`
            };
        } else {
            // Port in use by something else - find another port
            console.error(`[Docker] Port ${config.port} in use by another process`);
            const newPort = findAvailablePort(config.port + 1);
            if (!newPort) {
                return {
                    success: false,
                    port: null,
                    message: `Port ${config.port} is in use and no alternative ports available`
                };
            }
            config.port = newPort;
            console.error(`[Docker] Using alternative port: ${config.port}`);
        }
    }

    // Step 5: Check container status for configured name
    const status = getContainerStatus(config.containerName);
    console.error(`[Docker] Container "${config.containerName}" status: ${status}`);

    if (status === 'running') {
        // Already running, wait for healthy
        const healthy = await waitForHealthy(config.port, config.healthCheckTimeout);
        if (healthy) {
            writeCache({ port: config.port, containerName: config.containerName });
        }
        return {
            success: healthy,
            port: config.port,
            message: healthy ? 'Container already running' : 'Container running but not responding'
        };
    }

    if (status === 'stopped') {
        // Start existing container
        if (!startContainer(config.containerName)) {
            return {
                success: false,
                port: null,
                message: 'Failed to start existing container'
            };
        }
    } else {
        // Container doesn't exist - create new one
        // Only pull if image doesn't exist locally
        if (config.autoPull && !hasLocalImage(config.image)) {
            pullImage(config.image);
        }

        if (!createContainer(config)) {
            return {
                success: false,
                port: null,
                message: 'Failed to create container'
            };
        }
    }

    // Step 6: Wait for container to be healthy
    const healthy = await waitForHealthy(config.port, config.healthCheckTimeout);
    
    if (healthy) {
        // Save to cache for next time
        writeCache({ port: config.port, containerName: config.containerName });
    }
    
    return {
        success: healthy,
        port: config.port,
        message: healthy ? 'SearXNG container started successfully' : 'Container started but health check failed'
    };
}

/**
 * Setup cleanup handlers for graceful shutdown
 */
function setupCleanupHandlers(containerName, stopOnExit = false) {
    const cleanup = () => {
        if (stopOnExit) {
            console.error(`[Docker] Stopping container on exit...`);
            stopContainer(containerName);
        }
    };

    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);
    process.on('exit', cleanup);
}

module.exports = {
    ensureSearXNGRunning,
    setupCleanupHandlers,
    checkDockerInstalled,
    checkDockerRunning,
    getContainerStatus,
    findExistingSearXNGContainer,
    hasLocalImage,
    waitForHealthy,
    quickHealthCheck,
    readCache,
    writeCache,
    CACHE_FILE,
    DEFAULT_CONFIG
};
