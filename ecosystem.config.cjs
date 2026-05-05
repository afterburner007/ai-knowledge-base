module.exports = {
  apps: [{
    name: 'ai-kb',
    script: 'server_fastapi.py',
    interpreter: 'python3',
    cwd: '/home/ubuntu/code/ai-knowledge-base',
    instances: 1,
    exec_mode: 'fork',
    env: {
      APP_ENV: 'production',
      PORT: 8080,
      KB_CORS_ORIGINS: 'https://wiki.wudibyd.cloud',
    },
    error_file: '/var/log/ai-kb/error.log',
    out_file: '/var/log/ai-kb/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M'
  }]
};
