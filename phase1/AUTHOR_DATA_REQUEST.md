# Request to the original authors (draft, not sent)

**Status:** draft for Marwa Chnib to review and send herself. Nothing has been sent. Updated 2026-10-31 after the public search found none of these items (`DATASET_RECOVERY_REPORT.md`): the authors are the only remaining source.
- **To:** the corresponding author of Bhatia et al. (2024). Addresses are not filled in: take them from the published paper.
- **Cc:** Prof. Saraiva. Sending via the supervisor may help.
- **Attach:** the appendix below (the precise list), as a separate page.

---

**Subject:** Data request for a replication of "Unit Test Generation using Generative AI" (LLM4Code 2024)

Dear Shreya Bhatia, Tarushi Gandhi, Dhruv Kumar and Pankaj Jalote,

I am a PhD student at [university], working with Prof. [supervisor]. I am replicating your LLM4Code 2024 paper, "Unit Test Generation using Generative AI: A Comparative Performance Analysis of Autogeneration Tools" (DOI 10.1145/3643795.3648396). My replication uses open local language models alongside Pynguin and adds energy measurements.

Your repository (github.com/Rey-2001/LLM-nirvana) has been very helpful. With your stored suites and the same coverage commands, we reproduce all 77 stored small-set coverage reports exactly. A few items needed for a complete replication are not in it, and I would be grateful if you could share them:

1. **The large Category 1 modules (100–300 LOC).** The paper counts six (Section 2.2; Table 3). The repository contains one such module, `100_300 LOC p1/cat1/s15/example.py`. Could you share the other modules, or their source URLs? Please also say whether s15 is one of the six.

2. **The original ChatGPT results for Table 1.** These are the generated test files and coverage reports for the 0–100 LOC set, including the refactored Category 1 modules. Please also note which programs entered each category's mean: the folders hold 21 / 19 / 20 programs, against 20 per category in the paper.

3. **The p1 test files behind Tables 3 and 4.** These are the ChatGPT test suites of each improvement iteration and their coverage reports. Please also share the data used to classify incorrect assertions in Table 4, and say which dataset Table 4 uses.

4. **The Pynguin version used for the small set.** The compiled files suggest the small-set suites were generated on 3–4 August 2023, before Pynguin 0.34.0 was released. Could you confirm the version, or 0.33.0, and any non-default settings?

A few protocol details would also help us follow your method exactly:
- the ChatGPT model version and access dates;
- whether the two sentences of Figure 1 were typed together with the code as one message;
- whether each improvement iteration continued the same chat or started a new one;
- how incorrect assertions were counted in Table 4 (per assertion, or per failing test).

A precise list of the files is attached.

Any part of this would be useful, in whatever form is easiest for you. I will credit your contribution and cite the data as you prefer.

Thank you for your time and for making your materials public.

Kind regards,
Marwa Chnib
PhD student, [university]
[email]

---

## Appendix: precise list of missing items (to attach)

| # | Item | Paper result | In the public repository (commit e330b23) |
|---|---|---|---|
| 1 | The six large Category 1 modules (100–300 LOC), or their source URLs and commits; whether `100_300 LOC p1/cat1/s15/example.py` is one of them | Table 3 (Cat 1 row), Fig. 6 | at most one (s15) |
| 2 | ChatGPT test suites and coverage reports (statement and branch) for the 60 small programs | Table 1 (ChatGPT columns, p-values) | none |
| 3 | ChatGPT's refactored versions of the small Category 1 programs, with their tests | Table 1 ("Category 1 (refactored)") | none |
| 4 | Which programs entered each Table 1 mean (folders: 21 Cat 1 / 19 Cat 2 / 20 Cat 3; paper: 20 / 20 / 20) | Table 1 | not recorded |
| 5 | The ChatGPT test suite and coverage of every improvement iteration for the p1 modules (and the large Cat 1 modules) | Table 3, Fig. 6 | none |
| 6 | ChatGPT coverage reports of p2 samples 8 and 10, and which 40 samples Table 2's caption refers to (the means fit 41) | Table 2 | test files only |
| 7 | The assertion classification behind Table 4, and which dataset it uses | Table 4 | 43 compilation reports, 10 with tests that ran |
| 8 | Pynguin version and any non-default settings for the small set (files dated 3–4 Aug 2023) and for p2 | Tables 1, 2, 5 | not recorded |
| 9 | ChatGPT model version, access dates, and whether iterations shared one chat | all ChatGPT results | not recorded |
| 10 | If shareable: the two IIIT-Delhi B.Tech reports (handles 1531, 1552), which may list the modules | all | restricted access |
