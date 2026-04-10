#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Constants
const SEPARATOR = '='.repeat(60);

// Get the directory where this script is located
const scriptDir = __dirname;

// Path to the Python server
const serverPath = path.join(scriptDir, 'server.py');

// Check if Python is available
function checkPython() {
    const pythonCommands = ['python3', 'python'];
    
    for (const cmd of pythonCommands) {
        try {
            const result = require('child_process').spawnSync(cmd, ['--version'], { 
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
    
    return null;
}

// Check if dependencies are installed
function checkDependencies() {
    const reqPath = path.join(scriptDir, 'requirements.txt');
    if (!fs.existsSync(reqPath)) {
        console.error('❌ requirements.txt not found');
        return false;
    }
    
    // Check if key dependencies exist
    const pythonCmd = checkPython();
    if (!pythonCmd) {
        return false;
    }
    
    try {
        // Check for critical dependencies that server.py needs
        const result = require('child_process').spawnSync(
            pythonCmd, 
            ['-c', 'import starlette; import httpx; import uvicorn'], 
            {
                stdio: 'pipe',
                cwd: scriptDir
            }
        );
        
        return result.status === 0;
    } catch (e) {
        return false;
    }
}

// Install Python dependencies
function installDependencies(pythonCmd) {
    console.log('📦 Installing Python dependencies...');
    const reqPath = path.join(scriptDir, 'requirements.txt');
    
    const pip = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', reqPath], {
        stdio: 'inherit',
        cwd: scriptDir
    });
    
    return new Promise((resolve, reject) => {
        pip.on('close', (code) => {
            if (code === 0) {
                console.log('✅ Dependencies installed successfully');
                resolve();
            } else {
                console.error('❌ Failed to install dependencies');
                reject(new Error('Dependency installation failed'));
            }
        });
    });
}

// Main function
async function main() {
    console.log('🚀 SearXNG MCP Server (Enhanced Edition)');
    console.log(SEPARATOR);
    
    // Check Python
    const pythonCmd = checkPython();
    if (!pythonCmd) {
        console.error('❌ Python is not installed or not in PATH');
        console.error('   Please install Python 3.9 or newer');
        process.exit(1);
    }
    
    console.log(`✅ Found Python: ${pythonCmd}`);
    
    // Check if server.py exists
    if (!fs.existsSync(serverPath)) {
        console.error('❌ server.py not found');
        console.error(`   Expected at: ${serverPath}`);
        process.exit(1);
    }
    
    // Check and install dependencies if needed
    if (!checkDependencies()) {
        console.log('⚠️  Python dependencies not found');
        try {
            await installDependencies(pythonCmd);
        } catch (e) {
            console.error('❌ Failed to install dependencies');
            console.error('   Please run manually: pip install -r requirements.txt');
            process.exit(1);
        }
    } else {
        console.log('✅ Dependencies are installed');
    }
    
    // Get environment variables
    const env = {
        ...process.env,
        SEARXNG_BASE_URL: process.env.SEARXNG_BASE_URL || 'http://localhost:32768',
        HOST: process.env.HOST || '0.0.0.0',
        PORT: process.env.PORT || '32769',
        CONTENT_MAX_LENGTH: process.env.CONTENT_MAX_LENGTH || '10000',
        SEARCH_RESULT_LIMIT: process.env.SEARCH_RESULT_LIMIT || '10',
        DESIRED_TIMEZONE: process.env.DESIRED_TIMEZONE || 'UTC'
    };
    
    console.log('');
    console.log('Configuration:');
    console.log(`  SearXNG: ${env.SEARXNG_BASE_URL}`);
    console.log(`  Server: http://${env.HOST}:${env.PORT}`);
    console.log(`  Timezone: ${env.DESIRED_TIMEZONE}`);
    console.log(SEPARATOR);
    console.log('');
    
    // Start the Python server
    const server = spawn(pythonCmd, [serverPath], {
        stdio: 'inherit',
        cwd: scriptDir,
        env: env
    });
    
    // Handle process signals
    process.on('SIGINT', () => {
        console.log('\n👋 Shutting down...');
        server.kill('SIGINT');
        process.exit(0);
    });
    
    process.on('SIGTERM', () => {
        server.kill('SIGTERM');
        process.exit(0);
    });
    
    // Handle server exit
    server.on('close', (code) => {
        if (code !== 0) {
            console.error(`❌ Server exited with code ${code}`);
            process.exit(code);
        }
    });
}

// Run the server
main().catch(err => {
    console.error('❌ Error:', err.message);
    process.exit(1);
});
