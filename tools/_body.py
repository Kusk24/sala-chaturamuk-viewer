# -*- coding: utf-8 -*-
FIG_PLAN = '''<figure>
      <svg viewBox="0 0 320 300" role="img" aria-label="%s">
        <g stroke="currentColor" stroke-width="1.4" opacity=".38">%s</g>
        <g font-family="Archivo, sans-serif" font-size="10" fill="currentColor" opacity=".5"
           text-anchor="middle" dominant-baseline="middle">
          <text x="160" y="16">12</text><text x="302" y="150">3</text>
          <text x="160" y="284">6</text><text x="18" y="150">9</text>
        </g>
        <circle cx="160" cy="150" r="106" fill="none" stroke="currentColor"
                stroke-width=".8" opacity=".18" stroke-dasharray="3 4"/>
        <circle cx="160" cy="150" r="106" fill="none" stroke="#8F6516"
                stroke-width="5.5" stroke-linecap="round" stroke-dasharray="0.5 18.0"/>
        <path d="M146 122 h28 v14 h14 v28 h-14 v14 h-28 v-14 h-14 v-28 h14 Z"
              fill="currentColor" opacity=".18" stroke="currentColor" stroke-width="1.1"/>
        <circle cx="160" cy="150" r="3" fill="#8F6516"/>
        <g stroke="currentColor" opacity=".3" stroke-width=".9">
          <line x1="212" y1="150" x2="254" y2="150"/>
          <line x1="211.2" y1="159.0" x2="253.7" y2="166.5"/>
        </g>
        <text x="228" y="163" font-family="Archivo, sans-serif" font-size="9.5"
              fill="currentColor" opacity=".6" text-anchor="end">10&#176;</text>
        <g transform="translate(272 262)" stroke="#8F6516" fill="none" stroke-width="2">
          <path d="M0 -14 A 14 14 0 1 1 -12 7" marker-end="url(#ar)" stroke-linecap="round"/>
        </g>
      </svg>
      <figcaption>%s</figcaption>
    </figure>'''

TICKS = ''.join(
    '\n          <line x1="160" y1="24" x2="160" y2="32"%s/>' %
    ('' if a == 0 else ' transform="rotate(%d 160 150)"' % a)
    for a in range(0, 360, 30))

FIG_SIDE = '''<figure>
      <svg viewBox="0 0 380 205" role="img" aria-label="%s">
        <line x1="24" y1="180" x2="356" y2="180" stroke="currentColor" stroke-width="1.4" opacity=".5"/>
        <path d="M302 148 A 132 132 0 0 0 170 16" fill="none" stroke="currentColor"
              stroke-width="1" opacity=".25" stroke-dasharray="4 5"/>
        <g stroke="currentColor" opacity=".26" stroke-width=".9" stroke-dasharray="3 4">
          <line x1="297.5" y1="113.8" x2="170" y2="148"/>
          <line x1="271.1" y1="63.1" x2="170" y2="148"/>
        </g>
        <g stroke="#8F6516" opacity=".65" stroke-width=".9" stroke-dasharray="3 4">
          <line x1="225.8" y1="28.4" x2="170" y2="148"/>
          <line x1="181.5" y1="16.5" x2="170" y2="148"/>
        </g>
        <ellipse cx="170" cy="130" rx="38" ry="17" fill="none" stroke="#8F6516"
                 stroke-width="1.3" stroke-dasharray="4 4" opacity=".85"/>
        <g transform="translate(140 116)" color="currentColor" opacity=".85">
          <use href="#sala" width="60" height="64"/>
        </g>
        <g fill="currentColor" opacity=".72">
          <g transform="translate(297.5 113.8) rotate(165)"><rect x="-3.5" y="-11" width="7" height="22" rx="2"/></g>
          <g transform="translate(271.1 63.1) rotate(140)"><rect x="-3.5" y="-11" width="7" height="22" rx="2"/></g>
        </g>
        <g fill="#8F6516">
          <g transform="translate(225.8 28.4) rotate(115)"><rect x="-3.5" y="-11" width="7" height="22" rx="2"/></g>
          <g transform="translate(181.5 16.5) rotate(95)"><rect x="-3.5" y="-11" width="7" height="22" rx="2"/></g>
        </g>
        <g font-family="Archivo, sans-serif" font-size="11.5" font-weight="600">
          <text x="316" y="117" fill="currentColor" opacity=".7">15&#176;</text>
          <text x="288" y="62" fill="currentColor" opacity=".7">40&#176;</text>
          <text x="243" y="24" fill="#8F6516">65&#176;</text>
          <text x="196" y="13" fill="#8F6516">85&#176;</text>
        </g>
      </svg>
      <figcaption>%s</figcaption>
    </figure>'''

FIG_ZOOM = '''<figure>
      <svg viewBox="0 0 320 78" role="img" aria-label="%s">
        <rect x="46" y="15" width="228" height="48" rx="24" fill="currentColor" opacity=".07"/>
        <rect x="46" y="15" width="228" height="48" rx="24" fill="none" stroke="currentColor"
              stroke-width="1" opacity=".25"/>
        <g font-family="Archivo, sans-serif" font-size="15" text-anchor="middle" dominant-baseline="central">
          <text x="88" y="39" fill="currentColor" opacity=".45">.5</text>
          <line x1="76" y1="51" x2="100" y2="27" stroke="#9C2B21" stroke-width="2.2" stroke-linecap="round"/>
          <circle cx="160" cy="39" r="21" fill="#8F6516"/>
          <text x="160" y="39" fill="#FFF8E7" font-weight="700">1&#215;</text>
          <text x="218" y="39" fill="currentColor" opacity=".45">2</text>
          <line x1="206" y1="51" x2="230" y2="27" stroke="#9C2B21" stroke-width="2.2" stroke-linecap="round"/>
          <text x="256" y="39" fill="currentColor" opacity=".45">4</text>
          <line x1="246" y1="51" x2="266" y2="27" stroke="#9C2B21" stroke-width="2.2" stroke-linecap="round"/>
        </g>
      </svg>
      <figcaption>%s</figcaption>
    </figure>'''

FIG_FRAME = '''<figure>
      <svg viewBox="0 0 330 146" role="img" aria-label="%s">
        <g fill="none" stroke="currentColor" stroke-width="1.3" opacity=".42">
          <rect x="14" y="8" width="80" height="126" rx="9"/>
          <rect x="125" y="8" width="80" height="126" rx="9"/>
          <rect x="236" y="8" width="80" height="126" rx="9"/>
        </g>
        <g transform="translate(44 54)" color="currentColor" opacity=".72"><use href="#sala" width="20" height="21"/></g>
        <g transform="translate(133 40)" color="currentColor" opacity=".85"><use href="#sala" width="64" height="68"/></g>
        <clipPath id="%s"><rect x="237" y="9" width="78" height="124" rx="8"/></clipPath>
        <g clip-path="url(#%s)"><g transform="translate(224 18)" color="currentColor" opacity=".85"><use href="#sala" width="104" height="111"/></g></g>
        <g font-size="15" font-weight="700" text-anchor="middle" font-family="Archivo, sans-serif">
          <text x="54" y="130" fill="#9C2B21">&#10005;</text>
          <text x="165" y="130" fill="#2A6650">&#10003;</text>
          <text x="276" y="130" fill="#9C2B21">&#10005;</text>
        </g>
        <g transform="translate(299 24)">
          <circle cx="0" cy="0" r="9" fill="#9C2B21" opacity=".12"/>
          <g fill="#9C2B21"><circle cx="0" cy="-4.6" r="3"/><circle cx="4.4" cy="-1.4" r="3"/>
            <circle cx="2.7" cy="3.7" r="3"/><circle cx="-2.7" cy="3.7" r="3"/>
            <circle cx="-4.4" cy="-1.4" r="3"/></g>
        </g>
      </svg>
      <figcaption>%s</figcaption>
    </figure>'''
