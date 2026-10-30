# Request to the original authors (draft, not sent)

**Status:** draft for Marwa Chnib to review and send herself. Nothing has been sent.
- **To:** the corresponding author of Bhatia et al. (2024). Addresses are not filled in: take them from the published paper.
- **Cc:** Prof. Saraiva. Sending via the supervisor may help.
- **Attach:** `MISSING_DATA_LIMITATIONS.md`, if a detailed list helps.

---

**Subject:** Data request for a replication of "Unit Test Generation using Generative AI" (LLM4Code 2024)

Dear Shreya Bhatia, Tarushi Gandhi, Dhruv Kumar and Pankaj Jalote,

I am a PhD student at [university], working with Prof. [supervisor]. I am replicating your LLM4Code 2024 paper, "Unit Test Generation using Generative AI: A Comparative Performance Analysis of Autogeneration Tools" (DOI 10.1145/3643795.3648396). My replication uses open local language models alongside Pynguin and adds energy measurements.

Your repository (github.com/Rey-2001/LLM-nirvana) has been very helpful. With your stored suites and the same coverage commands, we reproduce all 77 stored small-set coverage reports exactly. A few items needed for a complete replication are not in it, and I would be grateful if you could share them:

1. **The large Category 1 modules (100–300 LOC).** The paper counts six (Section 2.2; Table 3). The repository contains one such module, `100_300 LOC p1/cat1/s15/example.py`. Could you share the other modules, or their source URLs? Please also say whether s15 is one of the six.

2. **The original ChatGPT results for Table 1.** These are the generated test files and coverage reports for the 0–100 LOC set, including the refactored Category 1 modules. Please also note which programs entered each category's mean: the folders hold 21 / 19 / 20 programs, against 20 per category in the paper.

3. **The p1 test files behind Tables 3 and 4.** These are the ChatGPT test suites of each improvement iteration and their coverage reports. Please also share the data used to classify incorrect assertions in Table 4, and say which dataset Table 4 uses.

4. **The Pynguin version used for the small set.** The compiled files suggest the small-set suites were generated on 3–4 August 2023, before Pynguin 0.34.0 was released. Could you confirm the version, or 0.33.0, and any non-default settings?

If ChatGPT's model version and access date are recorded, they would also help.

Any part of this would be useful, in whatever form is easiest for you. I will credit your contribution and cite the data as you prefer.

Thank you for your time and for making your materials public.

Kind regards,
Marwa Chnib
PhD student, [university]
[email]
