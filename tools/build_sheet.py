# -*- coding: utf-8 -*-
import io
exec(open('_body.py', encoding='utf-8').read())

DEFS = '''<svg width="0" height="0" aria-hidden="true" focusable="false" style="position:absolute">
  <defs>
    <symbol id="sala" viewBox="0 0 60 64">
      <path d="M11 27 C4 23 3 14 7 8 C7 15 10 21 15 24 Z" fill="currentColor" opacity=".9"/>
      <path d="M49 27 C56 23 57 14 53 8 C53 15 50 21 45 24 Z" fill="currentColor" opacity=".9"/>
      <path d="M30 4 L47 22 L13 22 Z" fill="currentColor" opacity=".9"/>
      <path d="M30 16 L54 34 L6 34 Z" fill="currentColor" opacity=".72"/>
      <rect x="17" y="34" width="26" height="13" fill="currentColor" opacity=".38"/>
      <rect x="21" y="36" width="3.5" height="11" fill="currentColor" opacity=".8"/>
      <rect x="35.5" y="36" width="3.5" height="11" fill="currentColor" opacity=".8"/>
      <rect x="11" y="47" width="38" height="5" fill="currentColor" opacity=".62"/>
      <rect x="6" y="52" width="48" height="6" fill="currentColor" opacity=".52"/>
      <rect x="24" y="58" width="12" height="4" fill="currentColor" opacity=".4"/>
    </symbol>
    <marker id="ar" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0 1 L9 5 L0 9 Z" fill="currentColor"/>
    </marker>
  </defs>
</svg>'''

EN = dict(
  cls='', numcls='',
  eyebrow='CSX4213 &#183; Sala Chaturamuk Phaichit &#183; Capture sheet',
  h1='Photographing the model',
  stand='One sitting, about 15 minutes. The only hard rule: every photograph from the <b>same phone, same lens, same session</b>.',
  kit=['iPhone 17 Pro', '1&#215; only', '~120 photos', '~15 min'],
  s1='Room', s1items=[
    'Pull the table <b>away from the cabinet</b>. You must be able to walk right behind it.',
    'Put a <b>patterned mat</b> under the model. <span class="why">Plain white gives the computer nothing to lock on to.</span>',
    'Both softboxes on, equal brightness. Do not move them once you start.',
    'Model and table stay still the whole time. Walk around it &#8212; never turn it.',
    'Nobody moving in the background.'],
  s2='Phone', s2items=[
    'Stay on <span class="ui">1&#215;</span>. Never 0.5&#215;, 2&#215; or 4&#215;. Never pinch to zoom.',
    'If a <b>flower icon</b> appears, tap it to switch macro off. <span class="why">Macro changes lens without telling you.</span>',
    'Live Photo <b>off</b>. Flash <b>off</b>.',
    'Photo mode. No Portrait, no Night, no filters.',
    'Stay 25 cm back. Tap the model once to focus before each circle.'],
  s3='Four circles', caption='Both hands, phone upright, 35&#8211;45 cm away.',
  th=['Circle', 'Looking down', 'Photos'],
  rows=[('1 &#8212; Low', 'crouched, level with the base', '15&#176;', '36', False),
        ('2 &#8212; Middle', 'standing, normal height', '40&#176;', '36', False),
        ('3 &#8212; High', 'phone raised above the roof', '65&#176;', '36', True),
        ('4 &#8212; Top', 'arm up, almost straight down', '85&#176;', '12', True)],
  s4='Every shot', s4items=[
    'Whole model in frame, a finger&#8217;s width of space all round.',
    'One short side-step between shots, about 10&#176;.',
    'Go behind it. The back matters as much as the front.',
    'Before you stop: check nothing is blurred, and that you can see the <b>top of the roof</b>.'],
  nev='Never', nevitems=[
    'Zoom, crop, edit or filter.',
    'Portrait mode, Night mode, flash.',
    'Turn the model instead of walking round it.',
    'Let your shadow fall on it.',
    'Send by Messenger, LINE or WhatsApp. <b>AirDrop</b>, or Drive at original quality.'],
  cap_plan='<b>36 photographs per circle.</b> A clock face on the table: one on every hour, two more between each pair.',
  cap_side='<b>The two gold circles are the ones people skip.</b> Our earlier capture had nothing from above, and the roof came out a blur.',
  cap_zoom='<b>One lens, start to finish.</b> Five earlier attempts failed on mixed lenses.',
  cap_frame='<b>Too far, right, too close.</b> The flower icon means the phone has changed lens.',
  aria_plan='Plan view: 36 evenly spaced camera positions in a circle around the model',
  aria_side='Side view: four camera heights at 15, 40, 65 and 85 degrees',
  aria_zoom='The zoom control with 1x circled and the others crossed out',
  aria_frame='Three phone frames: too small, correctly framed, cropped',
  foot=['One phone &#183; one lens &#183; one sitting', 'Sala Chaturamuk Phaichit &#183; tabletop model'],
  clip='clipA')

MY = dict(
  cls=' my', numcls=' my',
  eyebrow='CSX4213 &#183; စာလာ ချတုရမုခ် ဖိုက်ချစ် &#183; ဓာတ်ပုံရိုက်လမ်းညွှန်',
  h1='မော်ဒယ်ကို ဓာတ်ပုံရိုက်နည်း',
  stand='တစ်ကြိမ်တည်း၊ ၁၅ မိနစ်ခန့်။ စည်းကမ်းတစ်ခုတည်း — ဓာတ်ပုံအားလုံး <b>ဖုန်းတစ်လုံးတည်း၊ မှန်ဘီလူးတစ်ခုတည်း၊ တစ်ကြိမ်တည်း</b>မှ ရရမည်။',
  kit=['iPhone 17 Pro', '1&#215; သာ', 'ပုံ ၁၂၀ ခန့်', '၁၅ မိနစ်ခန့်'],
  s1='အခန်း', s1items=[
    'စားပွဲကို <b>ဗီရိုနှင့် ခွာ</b>ထားပါ။ နောက်ဘက်သို့ ဝင်လျှောက်နိုင်ရမည်။',
    'မော်ဒယ်အောက်တွင် <b>ပုံစံပါသော ဖျာ</b> ခင်းပါ။ <span class="why">အဖြူရောင်သက်သက်က ကွန်ပျူတာအတွက် မှတ်စရာ မရှိပါ။</span>',
    'Softbox နှစ်လုံးစလုံး ဖွင့်၊ အလင်းတူညီစေပါ။ စတင်ပြီးလျှင် မရွှေ့ပါနှင့်။',
    'မော်ဒယ်နှင့် စားပွဲ မရွှေ့ရ။ ကိုယ်တိုင် ပတ်လျှောက်ပါ — မော်ဒယ်ကို မလှည့်ရ။',
    'နောက်ခံတွင် လူ မသွားမလာစေရ။'],
  s2='ဖုန်း', s2items=[
    '<span class="ui">1&#215;</span> တွင်သာ ထားပါ။ 0.5&#215;၊ 2&#215;၊ 4&#215; မနှိပ်ရ။ ဆွဲချဲ့ခြင်း မလုပ်ရ။',
    '<b>ပန်းပွင့်ပုံ</b> ပေါ်လျှင် နှိပ်၍ Macro ပိတ်ပါ။ <span class="why">Macro က အသိမပေးဘဲ မှန်ဘီလူး ပြောင်းသည်။</span>',
    'Live Photo <b>ပိတ်</b>။ ဖလက်ရှ် <b>ပိတ်</b>။',
    'Photo မုဒ်သာ။ Portrait၊ Night၊ ဖီလ်တာ မသုံးရ။',
    '၂၅ စင်တီမီတာ ခွာပါ။ စက်ဝိုင်းမစမီ မော်ဒယ်ပေါ် တစ်ချက်နှိပ်၍ ဖိုကပ်ချပါ။'],
  s3='စက်ဝိုင်း လေးခု', caption='လက်နှစ်ဖက်၊ ဖုန်းမတ်မတ်၊ ၃၅–၄၅ စင်တီမီတာ ခွာပါ။',
  th=['စက်ဝိုင်း', 'အောက်ငုံ့ရန်', 'ပုံအရေအတွက်'],
  rows=[('၁ — နိမ့်', 'ကုန်း၍ အောက်ခံနှင့် ညီအောင်', '15&#176;', '၃၆', False),
        ('၂ — အလယ်', 'မတ်တပ်ရပ်', '40&#176;', '၃၆', False),
        ('၃ — မြင့်', 'ဖုန်းကို အမိုးထက် မြှောက်', '65&#176;', '၃၆', True),
        ('၄ — ထိပ်', 'လက်မြှောက်၍ တည့်တည့်နီးပါး', '85&#176;', '၁၂', True)],
  s4='ပုံတိုင်းအတွက်', s4items=[
    'မော်ဒယ်တစ်ခုလုံး ဘောင်ထဲဝင်ရမည်၊ ပတ်လည်တွင် လက်ညှိုးတစ်ချောင်းစာ နေရာလွတ်။',
    'ပုံတစ်ပုံနှင့်တစ်ပုံကြား တစ်လှမ်းစီ၊ ၁၀&#176; ခန့်။',
    'နောက်ဘက်ကိုပါ ပတ်ရိုက်ပါ။ နောက်ဘက်သည် ရှေ့ဘက်လောက်ပင် အရေးကြီးသည်။',
    'မရပ်မီ — ဝါးနေသောပုံ ရှိမရှိနှင့် <b>အမိုးထိပ်</b> မြင်ရမရ စစ်ပါ။'],
  nev='လုံးဝ မလုပ်ရန်', nevitems=[
    'ဆွဲချဲ့၊ ဖြတ်တောက်၊ တည်းဖြတ်၊ ဖီလ်တာ။',
    'Portrait မုဒ်၊ Night mode၊ ဖလက်ရှ်။',
    'ကိုယ်မလျှောက်ဘဲ မော်ဒယ်ကို လှည့်ခြင်း။',
    'ကိုယ့်အရိပ် မော်ဒယ်ပေါ် ကျခြင်း။',
    'Messenger၊ LINE၊ WhatsApp ဖြင့် ပို့ခြင်း။ <b>AirDrop</b> သို့မဟုတ် Drive (Original quality) သုံးပါ။'],
  cap_plan='<b>စက်ဝိုင်းတစ်ခုလျှင် ၃၆ ပုံ။</b> နာရီမျက်နှာပြင် မြင်ယောင်ပါ — ဂဏန်းတိုင်းတွင် တစ်ပုံ၊ ကြားတွင် နှစ်ပုံစီ။',
  cap_side='<b>ရွှေရောင် စက်ဝိုင်းနှစ်ခုကို လူများ ချန်တတ်သည်။</b> ယခင်တစ်ကြိမ်တွင် အပေါ်စီးမှ မရိုက်ခဲ့သဖြင့် အမိုး ဝါးသွားသည်။',
  cap_zoom='<b>အစအဆုံး မှန်ဘီလူးတစ်ခုတည်း။</b> ယခင် ငါးကြိမ် ပျက်ရသည်မှာ မှန်ဘီလူး ရောသုံးမိ၍။',
  cap_frame='<b>ဝေးလွန်း / မှန်ကန် / နီးလွန်း။</b> ပန်းပွင့်ပုံ ပေါ်လျှင် မှန်ဘီလူး ပြောင်းသွားပြီ။',
  aria_plan='အထက်မှမြင်ကွင်း — ကင်မရာနေရာ ၃၆ ခု',
  aria_side='ဘေးတိုက်မြင်ကွင်း — အမြင့် လေးဆင့်',
  aria_zoom='ဇူးမ်ခလုတ် — 1&#215; ကိုသာ သုံးရန်',
  aria_frame='ဖုန်းဘောင် သုံးမျိုး',
  foot=['ဖုန်းတစ်လုံး &#183; မှန်ဘီလူးတစ်ခု &#183; တစ်ကြိမ်တည်း', 'စာလာ ချတုရမုခ် ဖိုက်ချစ် &#183; စားပွဲတင်မော်ဒယ်'],
  clip='clipB')


def li(items):
    return '\n'.join('        <li>%s</li>' % t for t in items)


def sheet(d, nums):
    rows = '\n'.join(
        '            <tr%s><td><b>%s</b><br><span class="why">%s</span></td><td>%s</td><td class="n">%s</td></tr>'
        % (' class="key"' if key else '', a, b, c, n)
        for a, b, c, n, key in d['rows'])
    return '''<section class="sheet%(cls)s">
  <div class="head">
    <div class="eyebrow%(numcls)s">%(eyebrow)s</div>
    <h1%(numcls)s>%(h1)s</h1>
    <p class="stand">%(stand)s</p>
    <div class="kit">%(kit)s</div>
  </div>

  <div class="row">
    <div class="stack">
      <div>
        <h2%(numcls)s><span class="num">%(n1)s</span> %(s1)s</h2>
        <ul class="steps">
%(s1items)s
        </ul>
      </div>
      <div>
        <h2%(numcls)s><span class="num">%(n2)s</span> %(s2)s</h2>
        <ul class="steps">
%(s2items)s
        </ul>
      </div>
    </div>
    <div class="stack">
      %(fig_plan)s
      %(fig_zoom)s
    </div>
  </div>

  <div class="row">
    <div class="stack">
      <div>
        <h2%(numcls)s><span class="num">%(n3)s</span> %(s3)s</h2>
        <div class="tablewrap">
          <table>
            <caption>%(caption)s</caption>
            <thead><tr><th%(numcls)s>%(th0)s</th><th%(numcls)s>%(th1)s</th><th%(numcls)s>%(th2)s</th></tr></thead>
            <tbody>
%(rows)s
            </tbody>
          </table>
        </div>
      </div>
      <div>
        <h2%(numcls)s><span class="num">%(n4)s</span> %(s4)s</h2>
        <ul class="steps">
%(s4items)s
        </ul>
      </div>
    </div>
    <div class="stack">
      %(fig_side)s
      %(fig_frame)s
    </div>
  </div>

  <div class="box no">
    <h3%(numcls)s>%(nev)s</h3>
    <ul>
%(nevitems)s
    </ul>
  </div>

  <div class="foot"><span>%(f0)s</span><span>%(f1)s</span></div>
</section>''' % dict(
        cls=d['cls'], numcls=d['numcls'], eyebrow=d['eyebrow'], h1=d['h1'], stand=d['stand'],
        kit=''.join('<span>%s</span>' % k for k in d['kit']),
        n1=nums[0], n2=nums[1], n3=nums[2], n4=nums[3],
        s1=d['s1'], s1items=li(d['s1items']), s2=d['s2'], s2items=li(d['s2items']),
        s3=d['s3'], caption=d['caption'], th0=d['th'][0], th1=d['th'][1], th2=d['th'][2], rows=rows,
        s4=d['s4'], s4items=li(d['s4items']), nev=d['nev'], nevitems=li(d['nevitems']),
        f0=d['foot'][0], f1=d['foot'][1],
        fig_plan=FIG_PLAN % (d['aria_plan'], TICKS, d['cap_plan']),
        fig_side=FIG_SIDE % (d['aria_side'], d['cap_side']),
        fig_zoom=FIG_ZOOM % (d['aria_zoom'], d['cap_zoom']),
        fig_frame=FIG_FRAME % (d['aria_frame'], d['clip'], d['clip'], d['cap_frame']))


head = open('_head.txt', encoding='utf-8').read()
out = head + DEFS + '\n\n' + sheet(EN, '1234') + '\n\n' + sheet(MY, '၁၂၃၄') + '\n'
open('capture-sheet.html', 'w', encoding='utf-8').write(out)
open('preview.html', 'w', encoding='utf-8').write('<meta charset="utf-8">\n' + out)
print('written', len(out), 'chars')
