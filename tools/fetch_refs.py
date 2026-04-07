import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()
NOTION_TOKEN = os.getenv('NOTION_TOKEN')

pages = [
  {'id':'3367b6aa-8429-8005-90e0-d03db990a028','title':'상상','ref_type':'자사','product':'뉴턴젤리','content_type':'정보형'},
  {'id':'3367b6aa-8429-8015-80d2-cf116fe933a0','title':'정이엘','ref_type':'자사','product':'오메가3','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8021-a276-caa79e500ea5','title':'등급','ref_type':'자사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-803a-b0cf-f7e88be3decf','title':'비피젠_안녕하세요언니오빠','ref_type':'타사','product':'유산균','content_type':'오가닉'},
  {'id':'3367b6aa-8429-803d-aa6f-eca65ce72414','title':'찾아먹어','ref_type':'자사','product':'오메가3','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8048-b835-c04730dd7b87','title':'영양사','ref_type':'자사','product':'오메가3','content_type':'정보형'},
  {'id':'3367b6aa-8429-804c-bb44-c227f7dc7f2d','title':'비피젠_유산균아이','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-804d-aef1-c45bad474be9','title':'비피젠_대장독소','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-8053-9863-cf3b34605029','title':'비피젠_유명인필수','ref_type':'타사','product':'유산균','content_type':'커머셜'},
  {'id':'3367b6aa-8429-805a-bae3-ec2dd0ee7bf4','title':'비피젠_다크서클면역','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-805b-8bab-f19be94970a7','title':'고생','ref_type':'자사','product':'유산균','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8065-b7fb-c7abd336357e','title':'단약사','ref_type':'자사','product':'오메가3','content_type':'정보형'},
  {'id':'3367b6aa-8429-8066-8a15-da2053b97e46','title':'아이ADHD','ref_type':'타사','product':'','content_type':'커머셜'},
  {'id':'3367b6aa-8429-8073-ac7e-de0487f96c3e','title':'비피젠_455억마리','ref_type':'타사','product':'유산균','content_type':'커머셜'},
  {'id':'3367b6aa-8429-807b-8d0b-d5b20b76946e','title':'울보아들','ref_type':'자사','product':'뉴턴젤리','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8083-ac8f-ff0444c3ffa0','title':'퉤','ref_type':'자사','product':'오메가3','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8084-9c68-e6e26704a7f0','title':'도윤맘','ref_type':'자사','product':'뉴턴젤리','content_type':'오가닉'},
  {'id':'3367b6aa-8429-808e-931b-d72302885781','title':'새학기','ref_type':'자사','product':'유산균','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8093-9d3e-fb28decc1730','title':'잘시간','ref_type':'자사','product':'유산균','content_type':'오가닉'},
  {'id':'3367b6aa-8429-8095-af86-e5a981c4a355','title':'예민꿀템','ref_type':'자사','product':'뉴턴젤리','content_type':'정보형'},
  {'id':'3367b6aa-8429-809b-b069-e7792fa73ba9','title':'남편','ref_type':'자사','product':'뉴턴젤리','content_type':'커머셜'},
  {'id':'3367b6aa-8429-809d-b7c0-f819d3996306','title':'비피젠_응가피','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-80a2-ad17-cb4eaecb3538','title':'비피젠_100원딜이벤트','ref_type':'타사','product':'','content_type':'어그로'},
  {'id':'3367b6aa-8429-80a4-99c1-f7c87255dea5','title':'비피젠_이런사람은먹지마세요','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-80ab-b80a-d8bab31032f5','title':'비피젠_챗지피티','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-80ad-bd8b-e8348be207f1','title':'비피젠_대장병아이','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-80b3-b522-ef5ebe38cded','title':'김제연약사님','ref_type':'자사','product':'오메가3','content_type':'정보형'},
  {'id':'3367b6aa-8429-80bc-844c-f7d654534734','title':'드세요','ref_type':'자사','product':'뉴턴젤리','content_type':'정보형'},
  {'id':'3367b6aa-8429-80c5-87af-f86c418516c2','title':'김유니','ref_type':'자사','product':'오메가3','content_type':'오가닉'},
  {'id':'3367b6aa-8429-80c5-9dce-edb865732d6c','title':'비피젠_대장더러운아이특징','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-80c8-a01a-eac2468f3163','title':'필약사','ref_type':'자사','product':'오메가3','content_type':'정보형'},
  {'id':'3367b6aa-8429-80d2-99da-e7faaed14e61','title':'똥독','ref_type':'타사','product':'유산균','content_type':'정보형'},
  {'id':'3367b6aa-8429-80d4-93c4-fd2e08cca463','title':'AD전화','ref_type':'자사','product':'뉴턴젤리','content_type':'오가닉'},
  {'id':'3367b6aa-8429-80d6-9e9f-fb219354f65c','title':'속삭임','ref_type':'자사','product':'뉴턴젤리','content_type':'커머셜'},
  {'id':'3367b6aa-8429-80e3-bb0b-cc25b847c356','title':'비피젠_알러지','ref_type':'타사','product':'유산균','content_type':'커머셜'},
  {'id':'3367b6aa-8429-80e7-8df6-fb661fda8660','title':'편식','ref_type':'자사','product':'뉴턴젤리','content_type':'오가닉'},
  {'id':'3367b6aa-8429-80eb-bdbf-f1397cff9be3','title':'비피젠_토끼똥공주','ref_type':'타사','product':'유산균','content_type':'베네핏'},
]

def get_blocks(page_id):
    headers = {'Authorization': f'Bearer {NOTION_TOKEN}', 'Notion-Version': '2022-06-28'}
    req = urllib.request.Request(
        f'https://api.notion.com/v1/blocks/{page_id}/children?page_size=100', headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.load(r).get('results', [])

def extract(blocks):
    result = {'narration': [], 'fixed': [], 'flowing': [], 'visual': []}
    section = None
    for b in blocks:
        btype = b.get('type', '')
        if btype in ('heading_2', 'heading_3'):
            txt = ''.join(t.get('plain_text', '') for t in b.get(btype, {}).get('rich_text', []))
            if '나레이션' in txt:
                section = 'narration'
            elif '고정자막' in txt:
                section = 'fixed'
            elif '흘러가는' in txt:
                section = 'flowing'
            elif '영상소스' in txt:
                section = 'visual'
            else:
                section = None
        elif btype == 'bulleted_list_item' and section:
            txt = ''.join(t.get('plain_text', '') for t in b.get('bulleted_list_item', {}).get('rich_text', []))
            if txt:
                result[section].append(txt)
    return result

all_data = []
for i, p in enumerate(pages):
    print(f'({i+1}/{len(pages)}) {p["title"]}...', end=' ', flush=True)
    try:
        blocks = get_blocks(p['id'])
        extracted = extract(blocks)
        p['data'] = extracted
        print(f'나레이션{len(extracted["narration"])} 자막{len(extracted["flowing"])}')
    except Exception as e:
        print(f'ERROR: {e}')
        p['data'] = {'narration': [], 'fixed': [], 'flowing': [], 'visual': []}
    all_data.append(p)

with open('teams/contents/outputs/ref_all_data.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print(f'\n완료. {len(all_data)}개 저장.')
