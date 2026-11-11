# ShortsPilot AR 🇪🇬

مشروع سحابي لإنتاج YouTube Shorts عربية باستخدام PurffleShorts وGemini وEdge TTS وPixabay، مع اختبار رفع خاص وتحليل أداء القناة.

## الحالة التشغيلية الآمنة

- Workflow يدوي فقط عبر GitHub Actions؛ لا يوجد جدول نشر عام مفعّل.
- كل تشغيل ينتج فيديو واحدًا فقط.
- خصوصية الرفع `private` وحد النشر اليومي 1.
- الردود الآلية على التعليقات متوقفة.
- لا يتم تفعيل النشر العام أو 3 فيديوهات يوميًا قبل نجاح اختبار الرفع الخاص وموافقة صاحب القناة.
- سجل القناة يُستعاد ويُحفظ بين التشغيلات باستخدام GitHub Actions Cache، وتُرفق نسخة مع Artifact كل تشغيل.

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

الردود الآلية متوقفة. لا تفعّلها قبل إضافة تخزين دائم مجرّب ومنح صلاحية التعليقات بشكل منفصل.

## الترخيص

راجع ترخيص MIT وشروط PurffleShorts ومصادر الوسائط قبل إعادة الاستخدام أو التوزيع.
