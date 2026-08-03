/** Starter templates for Functions. */

export interface FunctionTemplate {
  id: string;
  name: string;
  description: string;
  auth_required: boolean;
  entrypoint: string;
  dependencies: string[];
  files: Record<string, string>;
}

export const FUNCTION_TEMPLATES: FunctionTemplate[] = [
  {
    id: 'hello',
    name: 'Hello JSON',
    description: 'Minimal authenticated handler that returns JSON.',
    auth_required: true,
    entrypoint: 'handler.py',
    dependencies: [],
    files: {
      'handler.py': `from snackbase_fn import Request, Response


def handler(req: Request) -> Response:
    return Response.json({
        "message": "hello from SnackBase Functions",
        "method": req.method,
        "user_id": req.auth.user_id,
    })
`,
    },
  },
  {
    id: 'webhook',
    name: 'Public webhook skeleton',
    description: 'Public endpoint skeleton for signature verification with a secret.',
    auth_required: false,
    entrypoint: 'handler.py',
    dependencies: [],
    files: {
      'handler.py': `import hashlib
import hmac
import os

from snackbase_fn import Request, Response

# Store the webhook signing secret as a Function Secret named WEBHOOK_SECRET.
# Never echo secrets or environment variables in the response.


def handler(req: Request) -> Response:
    secret = os.environ.get("WEBHOOK_SECRET", "")
    signature = req.headers.get("x-signature", "")
    body = req.body_bytes or b""
    if isinstance(body, str):
        body = body.encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(signature, expected):
        return Response.json({"error": "invalid signature"}, status=401)
    return Response.json({"received": True, "payload": req.json})
`,
    },
  },
  {
    id: 'openai',
    name: 'OpenAI chat',
    description: 'Calls OpenAI Chat Completions using a pinned SDK and OPENAI_API_KEY secret.',
    auth_required: true,
    entrypoint: 'handler.py',
    dependencies: ['openai==1.66.0'],
    files: {
      'handler.py': `import os

from snackbase_fn import Request, Response

# Requires Function Secret: OPENAI_API_KEY
# Deploy pin: openai==1.66.0


def handler(req: Request) -> Response:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = (req.json or {}).get("prompt", "Say hello")
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    text = completion.choices[0].message.content
    return Response.json({"reply": text})
`,
      'requirements.txt': 'openai==1.66.0\n',
    },
  },
];

export function getTemplate(id: string): FunctionTemplate | undefined {
  return FUNCTION_TEMPLATES.find((t) => t.id === id);
}
