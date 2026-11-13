# ShortsPilot AR 🇪🇬

مشروع آلي لإنتاج YouTube Shorts عربية باستخدام محرك PurffleShorts، ونماذج Groq مع بدائل اختيارية، وEdge TTS المصري، وPixabay، وGitHub Actions. يتضمن رفعًا إلى YouTube، وقراءة Analytics، وردودًا اختيارية على التعليقات، ولوحة إدارة تحتاج إلى نشر منفصل.

## إعداد التشغيل الحالي

الإعداد الفعلي في Workflow الحالي يستخدم `groq:openai/gpt-oss-120b` أساسيًا، ثم OpenRouter وDeepSeek وGemini كبدائل بالترتيب. البدائل التي لا توجد مفاتيحها في GitHub Secrets يتم تخطيها. Groq على الخطة الحالية قد يفرض حدًا قدره 8,000 token/minute؛ لذلك لا يمكن ضمان استمرار التوليد عند ضغط الاستخدام أو نفاد الحصة.

- GitHub Actions ينشئ Short واحدًا في كل تشغيل، مع جدول UTC ثلاث مرات يوميًا.
- الرفع مضبوط على `public`، والحد الداخلي الحالي 3 فيديوهات يوميًا؛ حدود YouTube الفعلية تظل هي الحاكمة.
- الموضوعات متنوعة: غرائب الحيوانات، «ماذا لو؟»، جسم الإنسان، العلوم، الفضاء، التاريخ، المحيطات والظواهر الطبيعية.
- مصادر الأفكار موزونة بين أسئلة بحث YouTube، أفكار متخصصة، Reddit، Google Trends وWikipedia، مع تجنب الأخبار الحساسة.
- تمت إضافة فحص لمدى تطابق وصف اللقطة مع كلمات المشهد؛ عند عدم وجود لقطة مناسبة يفضّل خلفية محايدة على فيديو مضلل.
- تحسينات العرض: Noto Sans Arabic، ترجمة karaoke، موضع سفلي، تدرج سينمائي، حركة Ken Burns وانتقالات قصيرة ومؤثرات صوتية.
- ملفات الفيديو المعلقة بسبب حد الرفع تُحفظ في Cache وتُعاد محاولة رفعها بعد التجديد؛ ملفات الفيديو المنشورة تُرفق كـ Artifact لمدة 14 يومًا.
- الردود الآلية على التعليقات تتخطى التشغيل إذا لم يكن السر المنفصل `YT_COMMENTS_TOKEN_JSON` مضبوطًا.

## الخدمات والمفاتيح

أضف الأسرار التالية من GitHub → Settings → Secrets and variables → Actions:

| Secret | الغرض |
|---|---|
| `YT_CLIENT_ID` | OAuth Client ID |
| `YT_CLIENT_SECRET` | OAuth Client Secret من نفس التطبيق |
| `YT_REFRESH_TOKEN` | Refresh token من نفس التطبيق |
| `GROQ_API_KEY` | مزود كتابة السكريبت الأساسي (مطلوب) |
| `OPENROUTER_API_KEY` | بديل احتياطي موصى بإضافته |
| `DEEPSEEK_API_KEY` | بديل احتياطي موصى بإضافته |
| `GEMINI_API_KEY` | بديل احتياطي؛ يخضع لحصة Google |
| `PIXABAY_API_KEY` | لقطات الفيديو |

لا ترسل أي قيمة سرية في المحادثة أو تضعها في ملفات المستودع.

### صلاحيات OAuth المطلوبة

استخدم OAuth Client وRefresh Token الحاليين اللذين اجتازا فحص التشغيل. لا تنشئ عميلًا جديدًا ولا تغيّر نوع التطبيق لمجرد هذا الدليل. يجب أن يتضمن التفويض الصلاحيات الثلاث التالية:

```
https://www.googleapis.com/auth/youtube.upload
https://www.googleapis.com/auth/youtube.readonly
https://www.googleapis.com/auth/yt-analytics.readonly
```

روابط الإعداد:
- [Google Cloud OAuth Clients](https://console.cloud.google.com/auth/clients)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground)
- [GitHub Actions Secrets](https://github.com/hussein0122/hussein/settings/secrets/actions)

إذا احتجت إلى إعادة التفويض، استخدم نفس نوع OAuth Client الذي أنشأته سابقًا، وسجّل Redirect URI المطلوب للأداة المستخدمة. فعّل YouTube Data API v3 وYouTube Analytics API في مشروع Google Cloud. لا ترسل Client Secret أو Refresh Token في المحادثة.

## خطوات التشغيل

1. شغّل **ShortsPilot AR - Automated Arabic Shorts** يدويًا من GitHub Actions أو من لوحة التحكم بعد إعدادها. تنبيه: إعداد الرفع الحالي `public`، لذلك التشغيل الناجح قد ينشر الفيديو للعامة.
2. يفحص الـ Workflow وجود الأسرار دون طباعة قيمها.
3. يختبر تجديد OAuth، وقراءة القناة، والوصول إلى YouTube Analytics.
4. يفحص توفر Gemini كبديل (وقد يفشل فحص الحصة دون إيقاف التشغيل)، ثم يختبر FFmpeg.
5. يجمع تقرير آخر 28 يومًا من المشاهدات ومتوسط نسبة المشاهدة ومدة المشاهدة المقدرة والإعجابات والتعليقات والمشتركين المكتسبين.
6. يشغّل PurffleShorts مع `LEARN_FROM_STATS=true` ليستخدم تاريخ المشاهدات والإعجابات والتعليقات في توجيه أفكار الفيديوهات التالية.
7. يحاول إنتاج ورفع فيديو واحد بخصوصية `public` حسب إعدادات الـworkflow الحالية.
8. يحفظ الفيديو والبيانات والتقرير كـ Artifact لمدة 14 يومًا، ويحفظ تاريخ القناة في Cache بين التشغيلات.

إذا لم تتوفر بيانات Analytics بعد، يُحفظ تقرير فارغ ويستمر الاختبار؛ قد تتأخر بيانات الفيديوهات الجديدة في YouTube Analytics.

## التعلم من النتائج

محرك PurffleShorts يحدّث أرقام المشاهدات والإعجابات والتعليقات للفيديوهات التي رفعها، ويستخدم أفضل وأسوأ الفيديوهات في توجيه السكريبتات التالية. يحتاج النظام إلى عدة فيديوهات ووقت كافٍ لتجميع بيانات ذات معنى.

تقرير Analytics الإضافي يسجل:
- Views
- Estimated minutes watched
- Average view duration
- Average view percentage
- Likes and comments
- Subscribers gained

مهم: التقرير يحفظ مقاييس الاحتفاظ ووقت المشاهدة لمراجعتها، لكن محرك PurffleShorts الحالي يوجّه كتابة المحتوى تلقائيًا باستخدام المشاهدات والإعجابات والتعليقات؛ لم نزعم أن متوسط الاحتفاظ يُستخدم بعدُ كعامل مباشر في اختيار السكريبت.

## الجدولة المستقبلية

الجدولة مفعلة حاليًا في ملف الـworkflow بثلاثة مواعيد يوميًا: 08:00 و14:00 و20:00 UTC. هذا يوافق 10:00 و16:00 و22:00 بتوقيت القاهرة في الشتاء، ويتغير ساعة مع التوقيت الصيفي. عدّل cron إذا أردت إيقاف الجدولة أو تغيير المواعيد.

## المجانية والتكاليف

- لا نستخدم توليد فيديو مدفوع.
- Gemini وPixabay وGitHub Actions لها حدود مجانية قابلة للتغيير.
- لا يتم تشغيل الفوترة أو شراء رصيد أو إضافة بطاقة.
- إذا تطلب أي مزود دفعًا أو تجاوزنا الحصة المجانية، يتوقف التشغيل بدلًا من الدفع تلقائيًا.
- لا يوجد ضمان للمشاهدات أو تحقيق الربح.

## التعليقات

الردود الآلية تستخدم ملف تفويض منفصلًا عن توكن رفع الفيديوهات، بصلاحية:
```
https://www.googleapis.com/auth/youtube.force-ssl
```
للتفعيل:
1. افتح [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) واضبطه لاستخدام OAuth Client الخاص بالمشروع.
2. اطلب النطاق `https://www.googleapis.com/auth/youtube.force-ssl` فقط، ثم أكمل التفويض واختر الوصول دون اتصال إذا ظهر الخيار.
3. نزّل ملف بيانات الاعتماد بصيغة JSON الذي يحتوي على refresh token.
4. في GitHub → Settings → Secrets and variables → Actions، أضف Secret باسم `YT_COMMENTS_TOKEN_JSON` وضع محتوى ملف JSON كاملًا كقيمته.
5. لا ترسل ملف JSON أو refresh token في المحادثة ولا تضعه داخل المستودع.

بعد إضافة السر، يحاول الـworkflow الرد على ما يصل إلى 20 تعليقًا يوميًا، مع تجاهل تعليقات القناة نفسها، وتسجيل معرفات التعليقات التي سبق الرد عليها في `data/comment_replies.sqlite3` المحفوظة في Actions Cache/Artifact. الردود محدودة ومحافظة؛ الأسئلة تحصل على رد يوضح أن المعلومة ستُراجع بدل اختلاق إجابة طبية. إذا لم يُضف السر، يتخطى البوت خطوة الردود دون تعطيل نشر الفيديو.

## الترخيص

راجع ترخيص MIT وشروط PurffleShorts ومصادر الوسائط قبل إعادة الاستخدام أو التوزيع.


## لوحة تحكم الأدمن

توجد واجهة إدارة في المجلد `dashboard/`، مع نقطة دخول Vercel في `app.py` وملف `vercel.json`. الواجهة ليست منشورة تلقائيًا؛ يجب نشرها وربط متغيرات البيئة يدويًا. كما يوجد ملف Blueprint بديل لـRender، لكنه ليس شرطًا لتشغيل البوت.

### إعداد النشر

1. افتح Vercel واستورد المستودع `hussein0122/hussein` من GitHub، واترك Root Directory في جذر المستودع.
2. في إعدادات Environment أضف المتغيرات التالية يدويًا:
   - `SESSION_SECRET`: قيمة عشوائية طويلة لا تقل عن 32 حرفًا.
   - `ADMIN_PASSWORD_HASH`: بصمة كلمة مرور جديدة خاصة بلوحة التحكم، وليست كلمة مرور Google.
   - `GITHUB_ACTIONS_TOKEN`: Fine-grained Personal Access Token لهذا المستودع فقط، مع صلاحية **Actions: Read and write** وMetadata: Read-only.
3. أنشئ بصمة كلمة المرور محليًا بعد تثبيت Flask:
   ```bash
   pip install "Flask>=3.1,<4"
   python -c "from werkzeug.security import generate_password_hash; import getpass; print(generate_password_hash(getpass.getpass('New dashboard password: '), method='scrypt'))"
   ```
   انسخ البصمة الناتجة فقط إلى `ADMIN_PASSWORD_HASH` في Vercel.
4. انشر المشروع واستخدم رابط Vercel الناتج. البريد المسموح الوحيد هو `husseinsead3@gmail.com`.

تعرض اللوحة آخر تشغيلات GitHub Actions، وحالة التشغيل، وتتيح إرسال طلب تشغيل يدوي وطلب إيقاف التشغيل الجاري بعد التحقق من أنه تابع لهذا الـworkflow. زر التشغيل قد ينشر فيديو عامًا لأن `YT_PRIVACY=public`. الواجهة متجاوبة مع الهاتف وتحدّث الحالة كل دقيقة. اللوحة غير منشورة حتى تكمل إعداد Vercel بنفسك.
لا تضع GitHub token أو كلمة المرور أو SESSION_SECRET في ملفات المستودع. نشر اللوحة يتطلب موافقتك داخل حساب Vercel وإضافة المتغيرات بنفسك؛ لوحة التحكم غير منشورة حتى يتم ذلك.
