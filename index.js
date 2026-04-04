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
    // Intercept gchk: button callbacks instantly, before Claude sees them.
    api.registerInteractiveHandler({
        channel: 'telegram',
        namespace: 'gchk',
        handler: async ({ callback, senderId }) => {
            const target = String(callback.chatId || senderId);
            try {
                callGrocery([
                    'handle-callback', callback.data,
                    '--target', target,
                    '--account', 'grocery',
                ]);
            } catch (err) {
                console.error('[grocery-checklist] callback error:', String(err));
            }
        },
    });

    // Expose render as a proper tool so Claude calls it reliably as a
    // function call rather than trying to compose a bash command.
    api.registerTool({
        name: 'render_grocery_view',
        label: 'Render Grocery View',
        description: 'Render the grocery shopping list or pantry view as a Telegram inline-keyboard message. Use mode "needed" for the shopping list, "all" for the full pantry.',
        parameters: {
            type: 'object',
            properties: {
                mode: {
                    type: 'string',
                    enum: ['needed', 'all'],
                    description: '"needed" = shopping list, "all" = pantry view',
                },
            },
            required: [],
        },
        async execute(_toolCallId, params, context) {
            const mode = params?.mode ?? 'needed';
            const account = 'grocery';
            // Derive the Telegram target from conversation context if available.
            const senderId = context?.senderId ?? context?.message?.senderId;
            const args = ['render-telegram', '--account', account, '--mode', mode];
            if (senderId) args.push('--target', String(senderId));
            try {
                callGrocery(args);
                return { ok: true };
            } catch (err) {
                return { ok: false, error: String(err) };
            }
        },
    }, { name: 'render_grocery_view' });
}
