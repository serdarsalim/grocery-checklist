import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const PLUGIN_DIR = path.dirname(fileURLToPath(import.meta.url));
const GROCERY_PY = path.join(PLUGIN_DIR, 'scripts', 'grocery.py');

function callGrocery(args) {
    const result = spawnSync('python3', [GROCERY_PY, ...args], {
        encoding: 'utf-8',
        timeout: 10_000,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        const msg = (result.stderr || result.stdout || '').trim();
        throw new Error(msg || `grocery.py exited with status ${result.status}`);
    }
    return result.stdout ? JSON.parse(result.stdout) : { ok: true };
}

export default function register(api) {
    api.registerInteractiveHandler({
        channel: 'telegram',
        namespace: 'gchk',
        handler: async ({ callback, senderId }) => {
            // callback.chatId is the chat where the message lives (== senderId for DMs)
            const target = String(callback.chatId || senderId);
            try {
                callGrocery([
                    'handle-callback', callback.data,
                    '--target', target,
                    '--account', 'grocery',
                ]);
            } catch (err) {
                // Log but don't crash — OpenClaw already answered the callback query
                console.error('[grocery-checklist] callback error:', String(err));
            }
        },
    });
}
