# -*- coding: utf-8 -*-
"""Drafted translations for the media replies in the client chat.

REVIEW_FIRST — machine-drafted, same standing as labels_extra.py and
labels_statement.py: fold in now so no client is answered in English on a
translated report, and promote into labels.py language by language as a
native speaker reviews them, at which point the reviewed string wins
automatically (merge is setdefault).

WHY A FOURTH LABEL FILE

Asking for a podcast or a presentation in the chat introduced nine strings
the label table had never seen — the two widget titles, the pending and
failed lines, the two "here it is" replies, the no-API-key line, and the
two "making it now" sentences. Every one is routed through labels.t, so the
machinery was already right and only the dictionary was short.

It matters more here than almost anywhere else in the product. These lines
are a REPLY: the client typed a sentence in their own language and the
system answers. A German question answered in English does not read as a
missing translation, it reads as not having been understood.

Kept apart from the other two because each file is one review unit —
labels_extra is the original 89 report strings, labels_statement the
custody-statement and headline terms, and this is the chat's media replies.
A reviewer signing off "Dutch is correct" should know which set they signed.

TWO JUDGEMENT CALLS, THE SAME ONES THE OTHER FILES MADE

"Podcast" stays "podcast" nearly everywhere, because it is the word those
markets actually use; coining a local equivalent nobody says would be worse
than leaving it. And the em dash in the two long sentences is kept as the
sentence break each language would naturally use, rather than transliterated
punctuation.
"""

from typing import Dict

REVIEW_FIRST = True

# The English source strings, exactly as api.py passes them to labels.t.
# If one of these is edited there it must be edited here, or the lookup
# silently misses and the client gets English back.
PODCAST_TITLE = "Your podcast"
VIDEO_TITLE = "Your presentation"
PENDING = "Preparing it now…"
FAILED = "That did not work this time. Please try again."
HERE_PODCAST = "Here is your podcast."
HERE_VIDEO = "Here is your presentation."
NO_KEY = "I cannot make that right now. Please try again in a moment."
MAKING_PODCAST = (
    "I am making your podcast now — it takes a minute or so, and it will "
    "play here as soon as it is ready."
)
MAKING_VIDEO = (
    "I am making your presentation now — it takes a minute or so, and it "
    "will play here as soon as it is ready."
)

_ORDER = (PODCAST_TITLE, VIDEO_TITLE, PENDING, FAILED, HERE_PODCAST,
          HERE_VIDEO, NO_KEY, MAKING_PODCAST, MAKING_VIDEO)

# locale -> the nine strings, in _ORDER.
_ROWS: Dict[str, tuple] = {
"de": ("Ihr Podcast", "Ihre Präsentation", "Wird jetzt erstellt …",
 "Das hat diesmal nicht geklappt. Bitte versuchen Sie es erneut.",
 "Hier ist Ihr Podcast.", "Hier ist Ihre Präsentation.",
 "Das kann ich gerade nicht erstellen. Bitte versuchen Sie es gleich noch einmal.",
 "Ich erstelle jetzt Ihren Podcast — das dauert etwa eine Minute, und er wird hier abgespielt, sobald er fertig ist.",
 "Ich erstelle jetzt Ihre Präsentation — das dauert etwa eine Minute, und sie wird hier abgespielt, sobald sie fertig ist."),
"nl": ("Uw podcast", "Uw presentatie", "Wordt nu gemaakt …",
 "Dat is deze keer niet gelukt. Probeer het opnieuw.",
 "Hier is uw podcast.", "Hier is uw presentatie.",
 "Dat kan ik nu niet maken. Probeer het zo meteen opnieuw.",
 "Ik maak nu uw podcast — dat duurt ongeveer een minuut, en hij speelt hier af zodra hij klaar is.",
 "Ik maak nu uw presentatie — dat duurt ongeveer een minuut, en hij speelt hier af zodra hij klaar is."),
"fr": ("Votre podcast", "Votre présentation", "Création en cours …",
 "Cela n’a pas fonctionné cette fois. Veuillez réessayer.",
 "Voici votre podcast.", "Voici votre présentation.",
 "Je ne peux pas le créer pour le moment. Réessayez dans un instant.",
 "Je crée votre podcast — cela prend environ une minute, et il sera lu ici dès qu’il sera prêt.",
 "Je crée votre présentation — cela prend environ une minute, et elle sera lue ici dès qu’elle sera prête."),
"es": ("Su pódcast", "Su presentación", "Creándolo ahora …",
 "Esta vez no ha funcionado. Vuelva a intentarlo.",
 "Aquí tiene su pódcast.", "Aquí tiene su presentación.",
 "Ahora no puedo crearlo. Vuelva a intentarlo en un momento.",
 "Estoy creando su pódcast — tarda un minuto aproximadamente y se reproducirá aquí en cuanto esté listo.",
 "Estoy creando su presentación — tarda un minuto aproximadamente y se reproducirá aquí en cuanto esté lista."),
"it": ("Il suo podcast", "La sua presentazione", "Creazione in corso …",
 "Questa volta non ha funzionato. Riprovi.",
 "Ecco il suo podcast.", "Ecco la sua presentazione.",
 "Al momento non posso crearlo. Riprovi tra poco.",
 "Sto creando il suo podcast — richiede circa un minuto e verrà riprodotto qui non appena sarà pronto.",
 "Sto creando la sua presentazione — richiede circa un minuto e verrà riprodotta qui non appena sarà pronta."),
"pt": ("O seu podcast", "A sua apresentação", "A criar agora …",
 "Desta vez não funcionou. Tente novamente.",
 "Aqui está o seu podcast.", "Aqui está a sua apresentação.",
 "Não consigo criar isso agora. Tente novamente dentro de momentos.",
 "Estou a criar o seu podcast — demora cerca de um minuto e será reproduzido aqui assim que estiver pronto.",
 "Estou a criar a sua apresentação — demora cerca de um minuto e será reproduzida aqui assim que estiver pronta."),
"da": ("Din podcast", "Din præsentation", "Oprettes nu …",
 "Det lykkedes ikke denne gang. Prøv igen.",
 "Her er din podcast.", "Her er din præsentation.",
 "Det kan jeg ikke lave lige nu. Prøv igen om et øjeblik.",
 "Jeg laver din podcast nu — det tager cirka et minut, og den afspilles her, så snart den er klar.",
 "Jeg laver din præsentation nu — det tager cirka et minut, og den afspilles her, så snart den er klar."),
"sv": ("Din podcast", "Din presentation", "Skapas nu …",
 "Det fungerade inte den här gången. Försök igen.",
 "Här är din podcast.", "Här är din presentation.",
 "Det kan jag inte skapa just nu. Försök igen om en stund.",
 "Jag skapar din podcast nu — det tar ungefär en minut, och den spelas upp här så snart den är klar.",
 "Jag skapar din presentation nu — det tar ungefär en minut, och den spelas upp här så snart den är klar."),
"nb": ("Din podkast", "Din presentasjon", "Lages nå …",
 "Det gikk ikke denne gangen. Prøv igjen.",
 "Her er podkasten din.", "Her er presentasjonen din.",
 "Det kan jeg ikke lage nå. Prøv igjen om et øyeblikk.",
 "Jeg lager podkasten din nå — det tar omtrent ett minutt, og den spilles av her så snart den er klar.",
 "Jeg lager presentasjonen din nå — det tar omtrent ett minutt, og den spilles av her så snart den er klar."),
"fi": ("Podcastisi", "Esityksesi", "Luodaan nyt …",
 "Tämä ei onnistunut tällä kertaa. Yritä uudelleen.",
 "Tässä on podcastisi.", "Tässä on esityksesi.",
 "En voi luoda sitä juuri nyt. Yritä hetken kuluttua uudelleen.",
 "Luon podcastiasi — se kestää noin minuutin, ja se toistetaan tässä heti kun se on valmis.",
 "Luon esitystäsi — se kestää noin minuutin, ja se toistetaan tässä heti kun se on valmis."),
"pl": ("Twój podcast", "Twoja prezentacja", "Trwa tworzenie …",
 "Tym razem się nie udało. Spróbuj ponownie.",
 "Oto Twój podcast.", "Oto Twoja prezentacja.",
 "Nie mogę tego teraz utworzyć. Spróbuj ponownie za chwilę.",
 "Tworzę Twój podcast — zajmie to około minuty i odtworzy się tutaj, gdy będzie gotowy.",
 "Tworzę Twoją prezentację — zajmie to około minuty i odtworzy się tutaj, gdy będzie gotowa."),
"cs": ("Váš podcast", "Vaše prezentace", "Právě se vytváří …",
 "Tentokrát se to nepodařilo. Zkuste to znovu.",
 "Zde je váš podcast.", "Zde je vaše prezentace.",
 "To teď nemohu vytvořit. Zkuste to za chvíli znovu.",
 "Vytvářím váš podcast — trvá to asi minutu a přehraje se zde, jakmile bude hotový.",
 "Vytvářím vaši prezentaci — trvá to asi minutu a přehraje se zde, jakmile bude hotová."),
"sk": ("Váš podcast", "Vaša prezentácia", "Práve sa vytvára …",
 "Tentoraz sa to nepodarilo. Skúste to znova.",
 "Tu je váš podcast.", "Tu je vaša prezentácia.",
 "To teraz nemôžem vytvoriť. Skúste to o chvíľu znova.",
 "Vytváram váš podcast — trvá to asi minútu a prehrá sa tu, len čo bude hotový.",
 "Vytváram vašu prezentáciu — trvá to asi minútu a prehrá sa tu, len čo bude hotová."),
"ru": ("Ваш подкаст", "Ваша презентация", "Создаётся …",
 "На этот раз не получилось. Попробуйте ещё раз.",
 "Вот ваш подкаст.", "Вот ваша презентация.",
 "Сейчас я не могу это создать. Попробуйте через минуту.",
 "Создаю ваш подкаст — это займёт около минуты, и он воспроизведётся здесь, как только будет готов.",
 "Создаю вашу презентацию — это займёт около минуты, и она воспроизведётся здесь, как только будет готова."),
"uk": ("Ваш подкаст", "Ваша презентація", "Створюється …",
 "Цього разу не вийшло. Спробуйте ще раз.",
 "Ось ваш подкаст.", "Ось ваша презентація.",
 "Зараз я не можу це створити. Спробуйте за хвилину.",
 "Створюю ваш подкаст — це займе близько хвилини, і він відтвориться тут, щойно буде готовий.",
 "Створюю вашу презентацію — це займе близько хвилини, і вона відтвориться тут, щойно буде готова."),
"bg": ("Вашият подкаст", "Вашата презентация", "Създава се …",
 "Този път не се получи. Опитайте отново.",
 "Ето вашия подкаст.", "Ето вашата презентация.",
 "В момента не мога да го създам. Опитайте отново след малко.",
 "Създавам вашия подкаст — отнема около минута и ще се възпроизведе тук веднага щом е готов.",
 "Създавам вашата презентация — отнема около минута и ще се възпроизведе тук веднага щом е готова."),
"ro": ("Podcastul dumneavoastră", "Prezentarea dumneavoastră",
 "Se creează acum …", "De data aceasta nu a funcționat. Încercați din nou.",
 "Iată podcastul dumneavoastră.", "Iată prezentarea dumneavoastră.",
 "Nu pot crea asta acum. Încercați din nou peste puțin timp.",
 "Creez podcastul dumneavoastră — durează aproximativ un minut și va fi redat aici imediat ce este gata.",
 "Creez prezentarea dumneavoastră — durează aproximativ un minut și va fi redată aici imediat ce este gata."),
"hu": ("Az Ön podcastja", "Az Ön prezentációja", "Készül …",
 "Ezúttal nem sikerült. Kérjük, próbálja újra.",
 "Itt van az Ön podcastja.", "Itt van az Ön prezentációja.",
 "Ezt most nem tudom elkészíteni. Kérjük, próbálja újra hamarosan.",
 "Most készítem a podcastját — körülbelül egy percet vesz igénybe, és itt fog lejátszódni, amint elkészül.",
 "Most készítem a prezentációját — körülbelül egy percet vesz igénybe, és itt fog lejátszódni, amint elkészül."),
"el": ("Το podcast σας", "Η παρουσίασή σας", "Δημιουργείται τώρα …",
 "Αυτή τη φορά δεν λειτούργησε. Δοκιμάστε ξανά.",
 "Ορίστε το podcast σας.", "Ορίστε η παρουσίασή σας.",
 "Δεν μπορώ να το δημιουργήσω αυτή τη στιγμή. Δοκιμάστε ξανά σε λίγο.",
 "Δημιουργώ το podcast σας — χρειάζεται περίπου ένα λεπτό και θα αναπαραχθεί εδώ μόλις είναι έτοιμο.",
 "Δημιουργώ την παρουσίασή σας — χρειάζεται περίπου ένα λεπτό και θα αναπαραχθεί εδώ μόλις είναι έτοιμη."),
"tr": ("Podcast’iniz", "Sunumunuz", "Şimdi hazırlanıyor …",
 "Bu sefer olmadı. Lütfen tekrar deneyin.",
 "İşte podcast’iniz.", "İşte sunumunuz.",
 "Bunu şu anda oluşturamıyorum. Lütfen birazdan tekrar deneyin.",
 "Podcast’inizi hazırlıyorum — yaklaşık bir dakika sürer ve hazır olur olmaz burada çalınacak.",
 "Sunumunuzu hazırlıyorum — yaklaşık bir dakika sürer ve hazır olur olmaz burada oynatılacak."),
"ar": ("البودكاست الخاص بك", "العرض التقديمي الخاص بك", "يتم إنشاؤه الآن …",
 "لم ينجح ذلك هذه المرة. يرجى المحاولة مرة أخرى.",
 "هذا هو البودكاست الخاص بك.", "هذا هو العرض التقديمي الخاص بك.",
 "لا يمكنني إنشاء ذلك الآن. يرجى المحاولة بعد قليل.",
 "أقوم بإنشاء البودكاست الخاص بك الآن — يستغرق ذلك دقيقة تقريبًا، وسيتم تشغيله هنا بمجرد أن يصبح جاهزًا.",
 "أقوم بإنشاء العرض التقديمي الخاص بك الآن — يستغرق ذلك دقيقة تقريبًا، وسيتم تشغيله هنا بمجرد أن يصبح جاهزًا."),
"he": ("הפודקאסט שלך", "המצגת שלך", "נוצר כעת …",
 "הפעם זה לא עבד. נסה שוב.",
 "הנה הפודקאסט שלך.", "הנה המצגת שלך.",
 "איני יכול ליצור זאת כעת. נסה שוב בעוד רגע.",
 "אני יוצר את הפודקאסט שלך — זה לוקח כדקה, והוא יתנגן כאן ברגע שיהיה מוכן.",
 "אני יוצר את המצגת שלך — זה לוקח כדקה, והיא תתנגן כאן ברגע שתהיה מוכנה."),
"fa": ("پادکست شما", "ارائه شما", "در حال ساخت …",
 "این بار موفق نبود. لطفاً دوباره تلاش کنید.",
 "این پادکست شماست.", "این ارائه شماست.",
 "در حال حاضر نمی‌توانم آن را بسازم. لطفاً کمی بعد دوباره تلاش کنید.",
 "در حال ساخت پادکست شما هستم — حدود یک دقیقه طول می‌کشد و به‌محض آماده شدن اینجا پخش می‌شود.",
 "در حال ساخت ارائه شما هستم — حدود یک دقیقه طول می‌کشد و به‌محض آماده شدن اینجا پخش می‌شود."),
"ur": ("آپ کا پوڈکاسٹ", "آپ کی پریزنٹیشن", "ابھی تیار کیا جا رہا ہے …",
 "اس بار یہ کام نہیں کر سکا۔ براہ کرم دوبارہ کوشش کریں۔",
 "یہ آپ کا پوڈکاسٹ ہے۔", "یہ آپ کی پریزنٹیشن ہے۔",
 "میں ابھی یہ نہیں بنا سکتا۔ براہ کرم تھوڑی دیر بعد دوبارہ کوشش کریں۔",
 "میں آپ کا پوڈکاسٹ بنا رہا ہوں — اس میں تقریباً ایک منٹ لگے گا، اور تیار ہوتے ہی یہ یہاں چلے گا۔",
 "میں آپ کی پریزنٹیشن بنا رہا ہوں — اس میں تقریباً ایک منٹ لگے گا، اور تیار ہوتے ہی یہ یہاں چلے گی۔"),
"ja": ("ポッドキャスト", "プレゼンテーション", "作成中です …",
 "今回はうまくいきませんでした。もう一度お試しください。",
 "ポッドキャストができました。", "プレゼンテーションができました。",
 "現在これを作成できません。しばらくしてからもう一度お試しください。",
 "ポッドキャストを作成しています — 1分ほどで完成し、できあがり次第ここで再生されます。",
 "プレゼンテーションを作成しています — 1分ほどで完成し、できあがり次第ここで再生されます。"),
"ko": ("팟캐스트", "프레젠테이션", "지금 만드는 중입니다 …",
 "이번에는 실패했습니다. 다시 시도해 주세요.",
 "팟캐스트가 준비되었습니다.", "프레젠테이션이 준비되었습니다.",
 "지금은 만들 수 없습니다. 잠시 후 다시 시도해 주세요.",
 "팟캐스트를 만들고 있습니다 — 1분 정도 걸리며, 준비되는 대로 여기에서 재생됩니다.",
 "프레젠테이션을 만들고 있습니다 — 1분 정도 걸리며, 준비되는 대로 여기에서 재생됩니다."),
"zh": ("您的播客", "您的演示文稿", "正在生成 …",
 "这次没有成功，请再试一次。",
 "这是您的播客。", "这是您的演示文稿。",
 "目前无法生成，请稍后再试。",
 "正在为您生成播客 — 大约需要一分钟，完成后将在此处播放。",
 "正在为您生成演示文稿 — 大约需要一分钟，完成后将在此处播放。"),
"zh-hant": ("您的播客", "您的簡報", "正在產生 …",
 "這次沒有成功，請再試一次。",
 "這是您的播客。", "這是您的簡報。",
 "目前無法產生，請稍後再試。",
 "正在為您產生播客 — 大約需要一分鐘，完成後將在此處播放。",
 "正在為您產生簡報 — 大約需要一分鐘，完成後將在此處播放。"),
"th": ("พอดแคสต์ของคุณ", "งานนำเสนอของคุณ", "กำลังสร้าง …",
 "ครั้งนี้ไม่สำเร็จ กรุณาลองอีกครั้ง",
 "นี่คือพอดแคสต์ของคุณ", "นี่คืองานนำเสนอของคุณ",
 "ขณะนี้ไม่สามารถสร้างได้ กรุณาลองใหม่อีกครั้งในอีกสักครู่",
 "กำลังสร้างพอดแคสต์ของคุณ — ใช้เวลาประมาณหนึ่งนาที และจะเล่นที่นี่ทันทีที่พร้อม",
 "กำลังสร้างงานนำเสนอของคุณ — ใช้เวลาประมาณหนึ่งนาที และจะเล่นที่นี่ทันทีที่พร้อม"),
"vi": ("Podcast của bạn", "Bản trình bày của bạn", "Đang tạo …",
 "Lần này không thành công. Vui lòng thử lại.",
 "Đây là podcast của bạn.", "Đây là bản trình bày của bạn.",
 "Hiện tôi không thể tạo. Vui lòng thử lại sau giây lát.",
 "Tôi đang tạo podcast của bạn — mất khoảng một phút, và sẽ phát ngay tại đây khi sẵn sàng.",
 "Tôi đang tạo bản trình bày của bạn — mất khoảng một phút, và sẽ phát ngay tại đây khi sẵn sàng."),
"id": ("Podcast Anda", "Presentasi Anda", "Sedang dibuat …",
 "Kali ini tidak berhasil. Silakan coba lagi.",
 "Ini podcast Anda.", "Ini presentasi Anda.",
 "Saya tidak dapat membuatnya sekarang. Silakan coba lagi sebentar lagi.",
 "Saya sedang membuat podcast Anda — perlu sekitar satu menit, dan akan diputar di sini begitu siap.",
 "Saya sedang membuat presentasi Anda — perlu sekitar satu menit, dan akan diputar di sini begitu siap."),
"ms": ("Podcast anda", "Pembentangan anda", "Sedang dibuat …",
 "Kali ini tidak berjaya. Sila cuba lagi.",
 "Ini podcast anda.", "Ini pembentangan anda.",
 "Saya tidak dapat membuatnya sekarang. Sila cuba lagi sebentar lagi.",
 "Saya sedang membuat podcast anda — mengambil masa kira-kira seminit, dan akan dimainkan di sini sebaik sahaja siap.",
 "Saya sedang membuat pembentangan anda — mengambil masa kira-kira seminit, dan akan dimainkan di sini sebaik sahaja siap."),
"tl": ("Ang inyong podcast", "Ang inyong presentasyon", "Ginagawa na …",
 "Hindi ito gumana sa pagkakataong ito. Pakisubukan muli.",
 "Narito ang inyong podcast.", "Narito ang inyong presentasyon.",
 "Hindi ko ito magawa ngayon. Pakisubukan muli maya-maya.",
 "Ginagawa ko na ang inyong podcast — aabutin ito ng humigit-kumulang isang minuto, at tutugtog dito kapag handa na.",
 "Ginagawa ko na ang inyong presentasyon — aabutin ito ng humigit-kumulang isang minuto, at tutugtog dito kapag handa na."),
"sw": ("Podikasti yako", "Wasilisho lako", "Inatengenezwa sasa …",
 "Haikufanya kazi safari hii. Tafadhali jaribu tena.",
 "Hii hapa podikasti yako.", "Hili hapa wasilisho lako.",
 "Siwezi kuitengeneza sasa hivi. Tafadhali jaribu tena baada ya muda mfupi.",
 "Ninatengeneza podikasti yako — inachukua kama dakika moja, na itachezwa hapa mara tu itakapokuwa tayari.",
 "Ninatengeneza wasilisho lako — linachukua kama dakika moja, na litachezwa hapa mara tu litakapokuwa tayari."),
"et": ("Teie taskuhääling", "Teie esitlus", "Luuakse praegu …",
 "Seekord ei õnnestunud. Palun proovige uuesti.",
 "Siin on teie taskuhääling.", "Siin on teie esitlus.",
 "Ma ei saa seda praegu luua. Palun proovige hetke pärast uuesti.",
 "Loon teie taskuhäälingut — see võtab umbes minuti ja mängitakse siin niipea, kui valmis on.",
 "Loon teie esitlust — see võtab umbes minuti ja mängitakse siin niipea, kui valmis on."),
"lv": ("Jūsu podkāsts", "Jūsu prezentācija", "Tiek veidots …",
 "Šoreiz neizdevās. Lūdzu, mēģiniet vēlreiz.",
 "Šeit ir jūsu podkāsts.", "Šeit ir jūsu prezentācija.",
 "Pašlaik nevaru to izveidot. Lūdzu, mēģiniet vēlreiz pēc brīža.",
 "Veidoju jūsu podkāstu — tas aizņem apmēram minūti, un tas tiks atskaņots šeit, tiklīdz būs gatavs.",
 "Veidoju jūsu prezentāciju — tā aizņem apmēram minūti, un tā tiks atskaņota šeit, tiklīdz būs gatava."),
"lt": ("Jūsų tinklalaidė", "Jūsų pristatymas", "Kuriama …",
 "Šįkart nepavyko. Bandykite dar kartą.",
 "Štai jūsų tinklalaidė.", "Štai jūsų pristatymas.",
 "Dabar to sukurti negaliu. Bandykite dar kartą po akimirkos.",
 "Kuriu jūsų tinklalaidę — tai užtruks apie minutę, ir ji bus paleista čia, kai tik bus paruošta.",
 "Kuriu jūsų pristatymą — tai užtruks apie minutę, ir jis bus paleistas čia, kai tik bus paruoštas."),
"sl": ("Vaš podkast", "Vaša predstavitev", "Se ustvarja …",
 "Tokrat ni uspelo. Poskusite znova.",
 "Tu je vaš podkast.", "Tu je vaša predstavitev.",
 "Tega zdaj ne morem ustvariti. Poskusite znova čez trenutek.",
 "Ustvarjam vaš podkast — traja približno minuto in se bo predvajal tukaj, takoj ko bo pripravljen.",
 "Ustvarjam vašo predstavitev — traja približno minuto in se bo predvajala tukaj, takoj ko bo pripravljena."),
"hr": ("Vaš podcast", "Vaša prezentacija", "Izrađuje se …",
 "Ovaj put nije uspjelo. Pokušajte ponovno.",
 "Evo vašeg podcasta.", "Evo vaše prezentacije.",
 "To trenutačno ne mogu izraditi. Pokušajte ponovno za koji trenutak.",
 "Izrađujem vaš podcast — traje otprilike minutu i reproducirat će se ovdje čim bude gotov.",
 "Izrađujem vašu prezentaciju — traje otprilike minutu i reproducirat će se ovdje čim bude gotova."),
"sr": ("Ваш подкаст", "Ваша презентација", "Управо се прави …",
 "Овај пут није успело. Покушајте поново.",
 "Ево вашег подкаста.", "Ево ваше презентације.",
 "Тренутно не могу то да направим. Покушајте поново за који тренутак.",
 "Правим ваш подкаст — траје око минут и биће пуштен овде чим буде готов.",
 "Правим вашу презентацију — траје око минут и биће пуштена овде чим буде готова."),
"bs": ("Vaš podcast", "Vaša prezentacija", "Upravo se pravi …",
 "Ovaj put nije uspjelo. Pokušajte ponovo.",
 "Evo vašeg podcasta.", "Evo vaše prezentacije.",
 "Trenutno to ne mogu napraviti. Pokušajte ponovo za koji trenutak.",
 "Pravim vaš podcast — traje oko minut i bit će pušten ovdje čim bude gotov.",
 "Pravim vašu prezentaciju — traje oko minut i bit će puštena ovdje čim bude gotova."),
"mk": ("Вашиот подкаст", "Вашата презентација", "Се создава …",
 "Овој пат не успеа. Обидете се повторно.",
 "Еве го вашиот подкаст.", "Еве ја вашата презентација.",
 "Моментално не можам да го создадам тоа. Обидете се повторно за малку.",
 "Го создавам вашиот подкаст — трае околу минута и ќе се пушти овде штом биде готов.",
 "Ја создавам вашата презентација — трае околу минута и ќе се пушти овде штом биде готова."),
"sq": ("Podkasti juaj", "Prezantimi juaj", "Po krijohet …",
 "Këtë herë nuk funksionoi. Ju lutemi provoni përsëri.",
 "Ja podkasti juaj.", "Ja prezantimi juaj.",
 "Nuk mund ta krijoj tani. Ju lutemi provoni përsëri pas pak.",
 "Po krijoj podkastin tuaj — zgjat rreth një minutë dhe do të luhet këtu sapo të jetë gati.",
 "Po krijoj prezantimin tuaj — zgjat rreth një minutë dhe do të luhet këtu sapo të jetë gati."),
"is": ("Hlaðvarpið þitt", "Kynningin þín", "Verið að búa til …",
 "Þetta tókst ekki í þetta sinn. Reyndu aftur.",
 "Hér er hlaðvarpið þitt.", "Hér er kynningin þín.",
 "Ég get ekki búið það til núna. Reyndu aftur eftir augnablik.",
 "Ég er að búa til hlaðvarpið þitt — það tekur um mínútu og spilast hér um leið og það er tilbúið.",
 "Ég er að búa til kynninguna þína — það tekur um mínútu og spilast hér um leið og hún er tilbúin."),
"bn": ("আপনার পডকাস্ট", "আপনার উপস্থাপনা", "এখন তৈরি হচ্ছে …",
 "এবার এটি কাজ করেনি। অনুগ্রহ করে আবার চেষ্টা করুন।",
 "এই যে আপনার পডকাস্ট।", "এই যে আপনার উপস্থাপনা।",
 "আমি এখন এটি তৈরি করতে পারছি না। অনুগ্রহ করে কিছুক্ষণ পরে আবার চেষ্টা করুন।",
 "আমি আপনার পডকাস্ট তৈরি করছি — প্রায় এক মিনিট সময় লাগবে, এবং প্রস্তুত হওয়ামাত্র এটি এখানে বাজবে।",
 "আমি আপনার উপস্থাপনা তৈরি করছি — প্রায় এক মিনিট সময় লাগবে, এবং প্রস্তুত হওয়ামাত্র এটি এখানে চলবে।"),
}


def merge_into(labels: Dict[str, Dict[str, str]]) -> None:
    """Fold these drafts into the main LABELS table.

    Same contract as labels_extra.merge_into and labels_statement.merge_into:
    never overwrites, so a string promoted into labels.py after review wins
    over the draft here, and this module can then be trimmed at leisure.
    """
    for lang, row in _ROWS.items():
        for english, translated in zip(_ORDER, row):
            labels.setdefault(english, {}).setdefault(lang, translated)
