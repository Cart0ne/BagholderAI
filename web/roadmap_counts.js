const fs = require('fs');
const html = fs.readFileSync('web/roadmap.html', 'utf8');
const match = html.match(/const ROADMAP = ({[\s\S]*?});/);
eval('var ROADMAP = ' + match[1]);
ROADMAP.phases.forEach(p => {
  const tasks = p.tasks.filter(t => t.section === undefined);
  const done = tasks.filter(t => t.status === 'done').length;
  console.log('Phase ' + p.id + ' | ' + p.title + ' | ' + done + '/' + tasks.length + ' | ' + p.status);
});
const all = ROADMAP.phases.flatMap(p => p.tasks.filter(t => t.section === undefined));
console.log('TOTAL | ' + all.filter(t => t.status === 'done').length + '/' + all.length);
