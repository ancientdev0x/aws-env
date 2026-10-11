# Submission checklist (Sun Oct 11)

Form: https://www.wemakedevs.org/aws/env/submit (sign in with the WeMakeDevs account; one submission per team).
Rules §04 (wemakedevs.org/aws/env/rules): public repo + YouTube demo video **under 3:00** (public or unlisted — open the
link in a signed-out browser first) + short writeup (problem, build, where AWS fits). §03: list the AI tools used.
Deadline hour: not published on the schedule page as of 2026-10-11 afternoon — **TO VERIFY on the form page**.

- [ ] Repo https://github.com/ancientdev0x/aws-env is public; README shows live URL, screenshot, architecture.
- [ ] `AWS_PROFILE=baadh scripts/reset_demo_state.sh` run after the last test; live URL loads and shows 7 cut-off.
- [ ] Video (≤ 3 min) uploaded (YouTube unlisted / Drive with view access) — link: ____
- [ ] Blog published on AWS Builder Center from docs/BLOG.md (attach docs/architecture.png, docs/screenshot.png) — link: ____
- [ ] AWS Builder Center student profile verified.
- [ ] Submission form: project name BaadhDrishti, Track 02 Heat & Water, repo link, live link, video link, blog link,
      AWS services: S3 (data bundle + static website hosting), API Gateway, Lambda, DynamoDB, SAM, AWS Open Data (Sentinel-1).
      (CloudFront is not used: the new account needs CloudFront verification — see CLAUDE.md.)
- [ ] After judging: deactivate the `baadh-dev` access key in IAM; `sam delete --stack-name baadhdrishti` when no longer needed.
