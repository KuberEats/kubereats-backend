import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const currentDir = dirname(fileURLToPath(import.meta.url))
const backendRoot = resolve(currentDir, '..')
const composeFile = resolve(backendRoot, '..', 'docker-compose.yml')

export default function setup() {
  if (process.env.KUBEREATS_SKIP_DB_RESET === '1') {
    return
  }

  if (process.env.KUBEREATS_DB_RESET_MODE === 'local') {
    resetWithLocalPython()
    return
  }

  resetWithDockerCompose()
}

function resetWithLocalPython() {
  try {
    execFileSync('uv', ['run', 'python', 'create_dummy_data.py'], {
      cwd: backendRoot,
      stdio: 'pipe',
      env: process.env,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)

    throw new Error(
      [
        'Failed to reset backend test data with local Python.',
        'Make sure PostgreSQL is running and DATABASE_URL is set.',
        `Original error: ${message}`,
      ].join('\n'),
    )
  }
}

function resetWithDockerCompose() {
  try {
    execFileSync(
      'docker',
      ['compose', '-f', composeFile, 'exec', '-T', 'backend', 'uv', 'run', 'python', 'create_dummy_data.py'],
      {
        cwd: backendRoot,
        stdio: 'pipe',
      },
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)

    throw new Error(
      [
        'Failed to reset backend test data.',
        'Start the backend stack first with: docker compose up -d postgres backend',
        `Original error: ${message}`,
      ].join('\n'),
    )
  }
}
