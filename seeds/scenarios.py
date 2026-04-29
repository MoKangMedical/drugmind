"""
DrugMind 种子数据
预设讨论场景 + 高质量话题，让社群冷启动有内容
"""

SEED_DISCUSSIONS = [
    {
        "topic": "GLP-1受体激动剂：口服 vs 注射，哪个技术路线更值得押注？",
        "tags": ["GLP-1", "剂型设计", "商业分析"],
        "context": "司美格鲁肽口服版(Rybelsus)证明了口服GLP-1可行性。诺和诺德、礼来、辉瑞都在布局。口服生物利用度仍是核心瓶颈。",
        "prompts": {
            "medicinal_chemist": "从药物化学角度，口服GLP-1面临的主要挑战是什么？渗透促进剂策略是否可持续？",
            "biologist": "口服GLP-1的体内活性与注射相比，差距有多大？如何设计合理的头对头实验？",
            "pharmacologist": "口服GLP-1的安全性考量，尤其是胃肠道副作用和长期肝毒性风险。",
            "data_scientist": "用ML模型预测口服生物利用度，哪些分子描述符最关键？",
            "project_lead": "综合评估：口服GLP-1赛道的商业前景、竞争格局和投资时机。",
        }
    },
    {
        "topic": "ADC药物：DS-8201之后，下一个重磅炸弹在哪里？",
        "tags": ["ADC", "靶点选择", "payload优化"],
        "context": "Enhertu(DS-8201)改变了HER2+乳腺癌治疗格局。目前有超过100个ADC在临床。关键问题：下一个突破性ADC需要什么？",
        "prompts": {
            "medicinal_chemist": "ADC的连接子(linker)设计趋势：可切割vs不可切割，亲水性优化如何影响PK？",
            "biologist": "除了HER2和TROP2，哪些靶点最有潜力成为下一个重磅ADC靶点？Claudin18.2？B7-H3？",
            "pharmacologist": "ADC的脱靶毒性问题——payload释放导致的血液学毒性和间质性肺炎如何预防？",
            "data_scientist": "用AI预测ADC的DAR(药物抗体比)与疗效/毒性的关系，目前数据够吗？",
            "project_lead": "ADC赛道已经很拥挤，新进入者的机会在哪里？差异化策略是什么？",
        }
    },
    {
        "topic": "AI生成的分子，合成不了怎么办？生成式AI与合成可行性的矛盾",
        "tags": ["AI生成", "合成化学", "SA Score"],
        "context": "扩散模型、VAE、GNN生成的分子看起来很好，但很多在化学上根本无法合成。这是AI制药最大的落地鸿沟。",
        "prompts": {
            "medicinal_chemist": "SA Score真的能评估合成难度吗？它的局限性是什么？更好的评估指标是什么？",
            "biologist": "如果AI生成的分子合成不了，要不要放宽筛选标准？还是坚持要求合成可行？",
            "pharmacologist": "合成路线复杂度如何影响杂质谱和CMC开发？",
            "data_scientist": "RetroSynthesis + AI：如何让生成模型在生成阶段就考虑合成可行性？RXN4Chemistry有帮助吗？",
            "project_lead": "这个问题导致了多少AI制药项目的失败？有没有成功案例？",
        }
    },
    {
        "topic": "靶点验证失败率80%：AI能解决这个根本问题吗？",
        "tags": ["靶点发现", "验证", "失败分析"],
        "context": "临床失败的最主要原因不是ADMET，而是靶点本身就不对。Nature Reviews Drug Discovery数据显示约50%的临床失败源于靶点验证不足。",
        "prompts": {
            "medicinal_chemist": "靶点不可成药(druggable)的判断标准在变化。以前认为不可成药的靶点，现在有新方法吗？PROTAC？分子胶？",
            "biologist": "CRISPR筛选 + 单细胞测序：如何用现代工具做更好的靶点验证？与传统siRNA的差异？",
            "pharmacologist": "靶点的安全性窗口：一个靶点在不同组织的表达差异如何影响治疗窗口？",
            "data_scientist": "OpenTargets + GWAS + 孟德尔随机化：AI如何整合多组学数据验证靶点？",
            "project_lead": "靶点验证阶段应该投入多少预算？什么标准才算'验证充分'可以进入筛选？",
        }
    },
    {
        "topic": "仿制药企转型创新药：AI是捷径还是陷阱？",
        "tags": ["商业模式", "仿制药转型", "中国药企"],
        "context": "中国大量仿制药企在寻求创新转型。恒瑞、百济神州已经成功，但更多企业还在探索。AI制药能否降低转型门槛？",
        "prompts": {
            "medicinal_chemist": "仿制药企的合成能力如何复用到创新药？CMC经验的优势和局限？",
            "biologist": "仿制药企通常缺乏靶点验证能力，AI能弥补多少？",
            "pharmacologist": "仿制药的安全性数据如何加速创新药的开发？真实世界数据(RWD)的价值？",
            "data_scientist": "仿制药企的数据基础（溶出度、BE数据）能用于AI建模吗？",
            "project_lead": "一家年营收10亿的仿制药企，如何用最小预算启动AI制药？最优策略是什么？",
        }
    },
    {
        "topic": "mRNA药物后疫情时代：从疫苗到肿瘤，下一步往哪走？",
        "tags": ["mRNA", "肿瘤免疫", "递送系统"],
        "context": "COVID疫苗验证了mRNA技术平台。Moderna/BioNTech都在拓展肿瘤疫苗、蛋白替代疗法等领域。LNP递送仍是核心瓶颈。",
        "prompts": {
            "medicinal_chemist": "mRNA序列优化：密码子优化、核苷酸修饰、UTR设计，哪个对表达量影响最大？",
            "biologist": "个性化肿瘤疫苗(neoantigen vaccine)：AI预测新抗原的准确率够用了吗？",
            "pharmacologist": "LNP的器官靶向性：除了肝脏，如何靶向肺、脾、肿瘤？",
            "data_scientist": "mRNA稳定性预测：用深度学习预测mRNA半衰期，目前最好的模型是什么？",
            "project_lead": "mRNA药物的CMC成本比小分子高很多，什么时候能降到可接受水平？",
        }
    },
    {
        "topic": "中国AI制药的真实困境：有技术没管线，怎么破？",
        "tags": ["中国AI制药", "商业模式", "管线建设"],
        "context": "中国有大量AI制药技术公司（晶泰、英矽智能、未知君等），但真正推进到临床的管线很少。技术落地的障碍到底在哪？",
        "prompts": {
            "medicinal_chemist": "中国CRO的合成能力全球领先，但为什么AI+合成的组合没有产生更多成功案例？",
            "biologist": "中国的基础研究投入很大，但靶点发现能力为什么还是跟在海外后面？",
            "pharmacologist": "中国创新药的临床开发策略跟海外有什么差异？AI能否帮助差异化？",
            "data_scientist": "中国缺乏高质量的药物研发数据集吗？还是数据分散在各处没有整合？",
            "project_lead": "如果给你1个亿，你会怎么建一个真正有竞争力的AI制药公司？",
        }
    },
    {
        "topic": "PROTAC vs 分子胶 vs 传统小分子：蛋白降解赛道该怎么选？",
        "tags": ["蛋白降解", "PROTAC", "分子胶"],
        "context": "Arvinas的PROTAC进展到临床III期，但分子胶(如Monte Rosa的VAV1降解剂)也在快速追赶。两种策略各有优劣。",
        "prompts": {
            "medicinal_chemist": "PROTAC的分子量太大(MW>700)，如何解决口服生物利用度问题？分子胶是否有天然优势？",
            "biologist": "E3连接酶的选择：CRBN vs VHL vs 其他？组织特异性E3连接酶的发现进展？",
            "pharmacologist": "PROTAC的hook效应(hook effect)如何在临床设计中规避？",
            "data_scientist": "用AI预测ternary complex的形成：目前有哪些计算方法和模型？",
            "project_lead": "PROTAC已经很热，作为新公司，进入分子胶是否更明智？",
        }
    },
]


SEED_ROLES = [
    {"role_id": "medicinal_chemist", "name": "陈化学家", "emoji": "🧪",
     "bio": "15年药物化学经验，曾任职诺华/罗氏，专攻抗肿瘤小分子"},
    {"role_id": "biologist", "name": "王生物", "emoji": "🔬",
     "bio": "分子生物学博士，专注靶点验证和功能基因组学"},
    {"role_id": "pharmacologist", "name": "李药理", "emoji": "💊",
     "bio": "临床药理专家，10年ADMET/毒理学经验"},
    {"role_id": "data_scientist", "name": "赵数据", "emoji": "📊",
     "bio": "AI制药算法工程师，专注分子生成和QSAR建模"},
    {"role_id": "project_lead", "name": "刘总监", "emoji": "📋",
     "bio": "制药项目管理15年，管理过3个从靶点到IND的完整项目"},
]


SEED_SCENARIOS = [
    {
        "name": "新靶点评估",
        "description": "拿到一个新的靶点，如何系统评估其成药性？",
        "checklist": [
            "文献调研：疾病关联性、遗传学证据",
            "结构评估：是否有可结合的口袋？",
            "竞争分析：已有多少项目？走到哪个阶段？",
            "差异化策略：me-better还是first-in-class？",
            "实验设计：最小可行验证实验",
            "Go/No-Go标准：什么数据支持推进？",
        ]
    },
    {
        "name": "先导化合物优化",
        "description": "Hit-to-Lead阶段的核心优化方向",
        "checklist": [
            "活性优化：IC50/EC50达到nM级别",
            "选择性评估：脱靶风险筛查",
            "ADMET初评：logP, solubility, metabolic stability",
            "hERG风险评估：IC50 > 30μM",
            "合成路线：SA Score < 5",
            "专利策略：结构新颖性分析",
        ]
    },
    {
        "name": "Go/No-Go决策",
        "description": "一个化合物是否应该继续投入？",
        "checklist": [
            "疗效数据：动物模型是否有效？",
            "安全性数据：毒理学评估结果？",
            "PK/PD：体内药代动力学是否支持每日一次给药？",
            "CMC可行性：能否放大生产？成本如何？",
            "竞争格局：同期竞品进展如何？",
            "商业评估：预期峰值销售是多少？",
        ]
    },
]
