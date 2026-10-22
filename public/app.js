let data, region = '전체';
const $ = s => document.querySelector(s);
function el(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className=cls; return n; }
function render() {
  const board = $('#board'); board.replaceChildren();
  const query = $('#search').value.trim().toLowerCase();
  const items = data.items.filter(x => (region === '전체' || x.region.startsWith(region)) && (x.name+' '+x.address).toLowerCase().includes(query));
  for (const status of ['접수 중','7일 내 접수','신규 공고']) {
    const column=el('section',undefined,'column'), entries=items.filter(x=>x.status===status);
    const heading=el('h2', status); heading.append(el('span',`${entries.length}건`,'count'));column.append(heading);
    if (!entries.length) column.append(el('p','해당 조건의 공고가 없습니다.','empty'));
    for(const item of entries) {
      const card=el('article',undefined,'card');card.append(el('span',item.region+(item.isNew?' · NEW':''),'pill'),el('h3',item.name),el('p',item.address||'주소 미제공','address'));
      const dates=el('div',undefined,'dates');dates.append(el('div',`접수 ${item.start||'미제공'} ~ ${item.end||'미제공'}`),el('div',`공급 ${item.units ?? '미제공'} 세대`),el('div',`당첨 발표 ${item.winner||'미제공'}`));card.append(dates);
      const link=el('a','공식 공고 ↗');link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';
      const image=el('a','카드 이미지 ↓');image.href=`cards/${encodeURIComponent(item.id)}.png`;image.download=`우더기네-${item.id}.png`;card.append(link,image);column.append(card);
    }board.append(column);
  }
}
async function start(){
 try { const response=await fetch('data.json',{cache:'no-store'});if(!response.ok)throw Error(); data=await response.json();if(!Array.isArray(data.items))throw Error();
 $('#updated').textContent=`마지막 갱신 ${new Date(data.updatedAt).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} · 한국시간`;
 const age=Date.now()-Date.parse(data.updatedAt);$('#notice').textContent=age>36*3600000?'갱신이 지연되었습니다. 지난 수집 결과입니다. 공식 공고에서 현재 일정을 확인하세요.':`최근 7일 신규 공고와 접수 중·향후 7일 내 접수 공고 ${data.items.length}건 · 단지는 접수 중 → 예정 → 신규 순으로 한 번만 표시합니다.`;
 render(); }catch{ $('#updated').textContent='아직 수집된 데이터가 없습니다.';$('#notice').textContent='실제 데이터 로드에 실패했습니다. GitHub Actions에서 API 비밀값과 최근 배포 결과를 확인하세요.';}
}
document.querySelectorAll('[data-region]').forEach(button=>button.addEventListener('click',()=>{region=button.dataset.region;document.querySelectorAll('[data-region]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));if(data)render();}));$('#search').addEventListener('input',()=>{if(data)render();});start();
