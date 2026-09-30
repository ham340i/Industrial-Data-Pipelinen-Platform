# Release 1 student review plan

Professor Rodrigo Morales Alvarado (`moar82`) is an academic reviewer, **not** a routine engineering reviewer or contributor. No professor workload is allocated. A planned reviewer in an issue is not evidence that a review occurred.

Primary owners and designated reviewers are recorded in every planned issue. The rotation advances one student in Iteration 1, two in Iteration 2, three in Iteration 3 and four in Iteration 4 using the supplied roster order. Extra early spikes follow the same rule. No owner reviews their own work; pairings change across iterations to share knowledge.

| Student | Planned review issues | Review hours |
|---|---|---:|
| ham340i | [#11](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/11), [#20](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/20), [#27](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/27), [#34](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/34) | 8 |
| aboudka2003 | [#4](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/4), [#21](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/21), [#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28), [#35](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/35) | 8 |
| adamoug | [#5](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/5), [#14](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/14), [#29](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/29), [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36) | 8 |
| Al-Yousef | [#6](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/6), [#12](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/12), [#15](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/15), [#22](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/22), [#37](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/37) | 9 |
| joedaswagger | [#7](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/7), [#16](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/16), [#23](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/23), [#30](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/30) | 8 |
| karimikhaeil | [#8](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/8), [#17](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/17), [#24](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/24), [#31](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/31) | 8 |
| MarcElHaddad1 | [#9](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/9), [#13](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/13), [#18](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/18), [#25](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/25), [#32](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/32) | 9 |
| menaboulus | [#10](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/10), [#19](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/19), [#26](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/26), [#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33) | 8 |


## Review procedure

1. Primary owner proposes contracts/alternatives early and asks the designated student for design feedback.
2. Implement on `feature/<issue>-short-name`, `fix/<issue>-short-name` or `docs/<issue>-short-name`; commit with the real issue reference and AI disclosure.
3. Include acceptance evidence, tests, CI, documentation, limitations and personal contribution in the PR.
4. Request the designated student on the actual PR when it is ready; this plan does not fabricate review requests or approvals.
5. Reviewer inspects design, correctness, failure cases, test assertions, data/credential boundaries and scope; record meaningful feedback.
6. Resolve comments, rerun checks, obtain independent approval and merge under main protection. Update real contribution/review records.

If unavailable, choose a different eligible student with capacity, update the issue and workload, and document the reason. Never substitute moar82 or self-approval. For high-risk SDK/data/security changes, involve a second student as an optional consulted reviewer without silently assigning unbudgeted work.
