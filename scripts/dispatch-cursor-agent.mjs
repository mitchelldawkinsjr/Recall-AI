#!/usr/bin/env node
/**
 * Dispatches a Cursor cloud agent to implement a GitHub issue.
 * Called from .github/workflows/issue-implement.yml when the `ready` label is applied.
 */
import { readFile, writeFile } from "node:fs/promises";
import { execSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Agent, CursorAgentError } from "@cursor/sdk";

const issueNumber = process.env.ISSUE_NUMBER;
const repo = process.env.REPO;
const apiKey = process.env.CURSOR_API_KEY;
const ghToken = process.env.GH_TOKEN;

if (!issueNumber || !repo || !apiKey || !ghToken) {
  console.error(
    "Missing required env: ISSUE_NUMBER, REPO, CURSOR_API_KEY, GH_TOKEN"
  );
  process.exit(1);
}

const issueUrl = `https://github.com/${repo}/issues/${issueNumber}`;
const repoUrl = `https://github.com/${repo}`;

function gh(args) {
  return execSync(`gh ${args}`, {
    encoding: "utf-8",
    env: { ...process.env, GH_TOKEN: ghToken },
    stdio: ["pipe", "pipe", "pipe"],
  });
}

async function ghIssueComment(body) {
  const tmp = join(tmpdir(), `issue-${issueNumber}-comment.md`);
  await writeFile(tmp, body, "utf-8");
  gh(`issue comment ${issueNumber} --repo ${repo} --body-file ${tmp}`);
}

const issue = JSON.parse(
  gh(`issue view ${issueNumber} --repo ${repo} --json title,body,labels,comments`)
);

const context = await readFile(".github/ai-implement-context.md", "utf-8");

const commentBodies = (issue.comments ?? [])
  .map((c) => c.body)
  .filter(Boolean)
  .join("\n\n---\n\n");

const prompt = `${context}

---

## Issue to implement

**URL:** ${issueUrl}
**Number:** #${issueNumber}
**Title:** ${issue.title}

### Issue body
${issue.body ?? "(empty)"}

### Comments (includes spec / acceptance criteria)
${commentBodies || "(no comments yet — read the issue body carefully)"}

Implement this issue now.

**Critical reminders:**
- Leave the PR as a **draft** — do NOT run \`gh pr ready\`. Bugbot + Ponytail run when \`pr-opened\` is applied (automatic on PR open).
- UI changes REQUIRE screenshots committed under \`artifacts/issue-${issueNumber}/\` and linked in the issue completion comment.
- When the PR is opened with \`Fixes #${issueNumber}\`, GitHub Actions clears \`agent-working\` and starts review — do NOT swap labels yourself.
- You MUST post the issue completion comment before stopping. Do not stop right after opening the PR.
`;

let agent;
try {
  agent = await Agent.create({
    apiKey,
    model: { id: "composer-2.5" },
    cloud: {
      repos: [{ url: repoUrl, startingRef: "main" }],
      autoCreatePR: true,
      skipReviewerRequest: true,
      envVars: {
        GH_TOKEN: ghToken,
      },
    },
    mcpServers: {
      github: {
        type: "stdio",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: { GITHUB_TOKEN: ghToken },
      },
    },
  });

  const run = await agent.send(prompt);
  console.log("Cloud agent started:", {
    agentId: agent.agentId,
    runId: run.id,
    issue: issueNumber,
  });

  await ghIssueComment(
    `🤖 **Cursor cloud agent started** for this issue.

- **Agent ID:** \`${agent.agentId}\`
- **Run ID:** \`${run.id}\`
- **Track progress:** [cursor.com/agents](https://cursor.com/agents)

The agent will implement the fix (PR stays draft until review bots finish), clear \`agent-working\` when the PR opens, post screenshots (if UI changed), and post a completion comment.`
  );
} catch (err) {
  if (err instanceof CursorAgentError) {
    console.error("Failed to start cloud agent:", err.message);
    try {
      gh(
        `issue edit ${issueNumber} --repo ${repo} --remove-label agent-working --add-label agent-failed --add-label ready`
      );
      await ghIssueComment(
        `❌ Cursor cloud agent **failed to start**: ${err.message}

Re-add the \`ready\` label after fixing the blocker (API key, repo access, etc.).`
      );
    } catch (ghErr) {
      console.error("Failed to update issue after agent error:", ghErr);
    }
    process.exit(1);
  }
  throw err;
} finally {
  if (agent) {
    await agent[Symbol.asyncDispose]();
  }
}
