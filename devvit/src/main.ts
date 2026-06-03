import { Devvit } from "@devvit/public-api";

const DEFAULT_STUDIO_URL = "https://redditmaker-studio.tech-760.workers.dev";
const MAX_COMMENTS = 40;
const MAX_COMMENT_LEN = 500;
const MIN_COMMENT_LEN = 1;

Devvit.configure({
  redditAPI: true,
  http: true,
});

Devvit.addSettings([
  {
    type: "string",
    name: "studioUrl",
    label: "URL do RedditMaker Studio",
    helpText: "Ex.: https://redditmaker-studio.tech-760.workers.dev",
    defaultValue: DEFAULT_STUDIO_URL,
  },
  {
    type: "string",
    name: "ingestSecret",
    label: "Chave de ingestão (STUDIO_INGEST_SECRET)",
    isSecret: true,
    helpText: "Mesma chave configurada no servidor do Studio",
  },
]);

type RedditComment = {
  body?: string;
  id?: string;
  permalink?: string;
};

function commentUrl(permalink: string | undefined, postId: string): string {
  if (!permalink) {
    return `https://www.reddit.com/comments/${postId}/`;
  }
  if (permalink.startsWith("http")) {
    return permalink;
  }
  return `https://www.reddit.com${permalink.startsWith("/") ? permalink : `/${permalink}`}`;
}

function mapComments(comments: RedditComment[], postId: string) {
  const out: { comment_body: string; comment_id: string; comment_url: string }[] = [];
  for (const c of comments) {
    const body = (c.body ?? "").trim();
    if (!body || body === "[removed]" || body === "[deleted]") {
      continue;
    }
    if (body.length < MIN_COMMENT_LEN || body.length > MAX_COMMENT_LEN) {
      continue;
    }
    const id = (c.id ?? "").replace(/[^\w-]/g, "");
    if (!id) {
      continue;
    }
    out.push({
      comment_body: body,
      comment_id: id,
      comment_url: commentUrl(c.permalink, postId),
    });
    if (out.length >= MAX_COMMENTS) {
      break;
    }
  }
  return out;
}

async function sendToStudio(
  context: Devvit.Context,
  payload: Record<string, unknown>,
): Promise<{ ok: boolean; message: string }> {
  const settings = await context.settings.getAll();
  const studioUrl = String(settings.studioUrl ?? DEFAULT_STUDIO_URL).replace(/\/$/, "");
  const secret = String(settings.ingestSecret ?? "").trim();

  if (!secret) {
    return {
      ok: false,
      message: "Configure a chave ingestSecret nas configurações do app.",
    };
  }

  const response = await fetch(`${studioUrl}/api/devvit/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${secret}`,
    },
    body: JSON.stringify({ ...payload, source: "devvit" }),
  });

  const text = await response.text();
  let data: { ok?: boolean; error?: string; message?: string; title?: string } = {};
  try {
    data = JSON.parse(text);
  } catch {
    data = { error: text.slice(0, 120) };
  }

  if (!response.ok) {
    return {
      ok: false,
      message: data.error ?? `HTTP ${response.status}`,
    };
  }

  return {
    ok: true,
    message: data.message ?? `Enfileirado: ${data.title ?? "thread"}`,
  };
}

Devvit.addMenuItem({
  label: "Enviar para RedditMaker Studio",
  location: "post",
  forUserType: "moderator",
  onPress: async (_event, context) => {
    const postId = context.postId;
    if (!postId) {
      context.ui.showToast("Abra o menu em um post.");
      return;
    }

    try {
      const post = await context.reddit.getPostById(postId);
      const listing = await context.reddit.getComments({
        postId,
        limit: MAX_COMMENTS + 10,
        sort: "top",
      });
      const raw = (await listing.all()) as RedditComment[];
      const comments = mapComments(raw, postId);
      const selftext = (post as { selftext?: string }).selftext?.trim() ?? "";
      const storymode = Boolean(selftext);

      const payload: Record<string, unknown> = {
        thread_id: postId,
        thread_title: post.title ?? "Sem título",
        thread_url: post.url?.startsWith("http")
          ? post.url
          : `https://www.reddit.com/comments/${postId}/`,
        is_nsfw: Boolean((post as { nsfw?: boolean }).nsfw ?? (post as { over18?: boolean }).over18),
        comments,
      };

      if (storymode) {
        payload.thread_post = selftext;
        payload.storymode = true;
      }

      if (!storymode && comments.length === 0) {
        context.ui.showToast("Post sem comentários válidos para vídeo.");
        return;
      }

      const result = await sendToStudio(context, payload);
      context.ui.showToast(result.message);
    } catch (err) {
      console.error(err);
      context.ui.showToast(`Erro: ${err instanceof Error ? err.message : String(err)}`);
    }
  },
});

export default Devvit;
