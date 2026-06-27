#!/usr/bin/env node
/**
 * Dispatches a Cursor cloud agent to review a PR (Bugbot or Ponytail).
 * Called from .github/workflows/pr-review.yml
 *
 * Env: REVIEW_TYPE=bugbot|ponytail, PR_NUMBER, PR_HEAD_REF, REPO, CURSOR_API_KEY, GH_TOKEN
 * Optional: ISSUE_NUMBER (for workflow status output)
 */
import { readFile, appendFile, writeFile, mkdtemp } from "node:fs/promises";
import { execSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Agent, CursorAgentError } from "@cursor/sdk";

const reviewType = process.env.REVIEW_TYPE;
const prNumber = process.env.PR_NUMBER;
const prHeadRef = process.env.PR_HEAD_REF;
const repo = process.env.REPO;
const apiKey = process.env.CURSOR_API_KEY;
const ghToken = process.env.GH_TOKEN;
const githubOutput = process.env.GITHUB_OUTPUT;

const CONTEXT_FILES = {
  bugbot: ".github/ai-bugbot-context.md",
  ponytail: ".github/ai-ponytail-review-context.md",
};

const REVIEW_HEADERS = {
  bugbot: "## Bugbot review",
  ponytail: "## Ponytail review",
};

if (!reviewType || !CONTEXT_FILES[reviewType]) {
  console.error("REVIEW_TYPE must be bugbot or ponytail");
  process.exit(1);
}
if (!prNumber || !prHeadRef || !repo || !apiKey || !ghToken) {
  console.error(
    "Missing required env: REVIEW_TYPE, PR_NUMBER, PR_HEAD_REF, REPO, CURSOR_API_KEY, GH_TOKEN"
  );
  process.exit(1);
}

const repoUrl = `https://github.com/${repo}`;
const prUrl = `${repoUrl}/pull/${prNumber}`;

function gh(args) {
  return execSync(`gh ${args}`, {
    encoding: "utf-8",
    env: { ...process.env, GH_TOKEN: ghToken },
    stdio: ["pipe", "pipe", "pipe"],
  });
}

async function writeGithubOutput(key, value) {
  if (githubOutput) {
    await appendFile(githubOutput, `${key}=${value}\n`);
  }
}

function parseReviewOutput(text, reviewType) {
  const statusMatch = text.match(/REVIEW_STATUS=(clean|findings)/);
  if (!statusMatch) {
    throw new Error("Agent output missing REVIEW_STATUS=clean|findings");
  }

  const blockMatch = text.match(
    /REVIEW_COMMENT_START\s*\n([\s\S]*?)\nREVIEW_COMMENT_END/
  );
  if (blockMatch) {
    const body = blockMatch[1].trim();
    if (!body) {
      throw new Error("Agent output had empty REVIEW_COMMENT block");
    }
    return { body, hasFindings: statusMatch[1] === "findings" };
  }

  const header = REVIEW_HEADERS[reviewType];
  const headerIndex = text.indexOf(header);
  if (headerIndex !== -1) {
    const statusIndex = text.indexOf("REVIEW_STATUS=", headerIndex);
    const body =
      statusIndex === -1
        ? text.slice(headerIndex).trim()
        : text.slice(headerIndex, statusIndex).trim();
    if (body) {
      return { body, hasFindings: statusMatch[1] === "findings" };
    }
  }

  throw new Error(
    "Agent output missing REVIEW_COMMENT block (REVIEW_COMMENT_START/END)"
  );
}

async function postPrComment(body) {
  const dir = await mkdtemp(join(tmpdir(), "pr-review-"));
  const file = join(dir, "comment.md");
  await writeFile(file, body, "utf-8");
  gh(`pr comment ${prNumber} --repo ${repo} --body-file ${file}`);
}

async function collectAgentText(run, result) {
  let text = result.result ?? "";
  if (!/REVIEW_STATUS=(clean|findings)/.test(text)) {
    try {
      if (run.supports("conversation")) {
        const turns = await run.conversation();
        for (let i = turns.length - 1; i >= 0; i--) {
          const turn = turns[i];
          if (turn.type === "assistant_message" && turn.text) {
            text = turn.text;
            break;
          }
        }
      }
    } catch {
      // use result.result as-is
    }
  }
  return text;
}

const pr = JSON.parse(
  gh(`pr view ${prNumber} --repo ${repo} --json title,body,baseRefName`)
);

const context = await readFile(CONTEXT_FILES[reviewType], "utf-8");
const reviewLabel = reviewType === "bugbot" ? "Bugbot" : "Ponytail";

const prompt = `${context}

---

## Pull request to review

**URL:** ${prUrl}
**Number:** #${prNumber}
**Head branch:** \`${prHeadRef}\`
**Base branch:** \`${pr.baseRefName ?? "main"}\`
**Title:** ${pr.title}

### PR body
${pr.body ?? "(empty)"}

Review this PR now. Return your comment between REVIEW_COMMENT_START and REVIEW_COMMENT_END, then end with REVIEW_STATUS=clean or REVIEW_STATUS=findings. Do not run gh or post comments yourself.
`;

let agent;
try {
  agent = await Agent.create({
    apiKey,
    model: { id: "composer-2.5" },
    cloud: {
      repos: [{ url: repoUrl, startingRef: prHeadRef }],
      autoCreatePR: false,
      skipReviewerRequest: true,
    },
  });

  console.log(`Starting ${reviewLabel} review for PR #${prNumber} (${prHeadRef})`);
  const run = await agent.send(prompt);
  console.log({ agentId: agent.agentId, runId: run.id, reviewType, pr: prNumber });

  const result = await run.wait();
  if (result.status === "error") {
    console.error(`${reviewLabel} run failed:`, result.id);
    await writeGithubOutput("has_findings", "error");
    process.exit(2);
  }

  const text = await collectAgentText(run, result);
  const { body, hasFindings } = parseReviewOutput(text, reviewType);

  await postPrComment(body);
  console.log(`Posted ${reviewLabel} comment on PR #${prNumber}`);

  await writeGithubOutput("has_findings", hasFindings ? "true" : "false");
  console.log(`${reviewLabel} complete: has_findings=${hasFindings}`);
} catch (err) {
  if (err instanceof CursorAgentError) {
    console.error(`Failed to start ${reviewLabel} agent:`, err.message);
    await writeGithubOutput("has_findings", "error");
    process.exit(1);
  }
  console.error(`${reviewLabel} failed:`, err.message ?? err);
  await writeGithubOutput("has_findings", "error");
  process.exit(1);
} finally {
  if (agent) {
    await agent[Symbol.asyncDispose]();
  }
}
