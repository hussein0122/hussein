# ShortsPilot AR 🇪🇬

مشروع سحابي لإنتاج YouTube Shorts عربية باستخدام PurffleShorts وGemini وEdge TTS وPixabay، مع اختبار رفع خاص وتحليل أداء القناة.

## إعداد التشغيل الحالي

نستخدم `gemini-3.5-flash-lite` مع Edge TTS المصري وPixabay، من دون تفعيل فوترة مدفوعة.

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
| `GEMINI_API_KEY` | كتابة السكريبت عبر Google AI Studio |
| `PIXABAY_API_KEY` | لقطات الفيديو |

لا ترسل أي قيمة سرية في المحادثة أو تضعها في ملفات المستودع.

### صلاحيات OAuth المطلوبة

يجب إنشاء Refresh Token باستخدام نفس OAuth Web Client ID وSecret، وبالصلاحيات الثلاث التالية:

```
https://www.googleapis.com/auth/youtube.upload
https://www.googleapis.com/auth/youtube.readonly
https://www.googleapis.com/auth/yt-analytics.readonly
```

روابط الإعداد:
- [Google Cloud OAuth Clients](https://console.cloud.google.com/auth/clients)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground)
- [GitHub Actions Secrets](https://github.com/hussein0122/hussein/settings/secrets/actions)

في OAuth Playground استخدم بيانات OAuth الخاصة بك، وتأكد أن Redirect URI الخاص بـ Playground مسجل في OAuth Web Client. فعّل YouTube Data API v3 وYouTube Analytics API في مشروع Google Cloud. لا تفعّل الفوترة ولا تضف بطاقة.

## خطوات التشغيل

1. شغّل **Arabic Shorts - safe test** يدويًا من GitHub Actions.
2. يفحص الـ Workflow وجود الأسرار دون طباعة قيمها.
3. يختبر تجديد OAuth، وقراءة القناة، والوصول إلى YouTube Analytics.
4. يختبر Gemini ثم FFmpeg.
5. يجمع تقرير آخر 28 يومًا من المشاهدات ومتوسط نسبة المشاهدة ومدة المشاهدة المقدرة والإعجابات والتعليقات والمشتركين المكتسبين.
6. يشغّل PurffleShorts مع `LEARN_FROM_STATS=true` ليستخدم تاريخ المشاهدات والإعجابات والتعليقات في توجيه أفكار الفيديوهات التالية.
7. يحاول إنتاج ورفع فيديو واحد بخصوصية Private.
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

بعد التأكد من نجاح الرفع الخاص وجودة الفيديو، يمكن إضافة ثلاثة تشغيلات يوميًا حسب نشاط جمهور القناة. GitHub Actions Cron يعمل بتوقيت UTC؛ يجب حساب مواعيد القاهرة مع مراعاة التوقيت الصيفي المصري. الجدولة غير مفعلة حاليًا عمدًا.

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
