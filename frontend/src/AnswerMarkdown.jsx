import React from 'react';

function unescapeMarkdown(value) {
  return value.replace(/\\([\\`*_{}\[\]()#+\-.!|>])/g, '$1');
}

function renderInline(value, keyPrefix) {
  const parts = unescapeMarkdown(value).split(/(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__)/g);
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function isBlockStart(line) {
  const normalized = unescapeMarkdown(line);
  return /^ {0,3}```/.test(line)
    || /^ {0,3}#{1,6}\s+/.test(normalized)
    || /^\s*(?:[-*+]\s+|\d+[.)]\s+)/.test(normalized);
}

export default function AnswerMarkdown({ text }) {
  const lines = (typeof text === 'string' ? text : '').split(/\r?\n/);
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const normalized = unescapeMarkdown(line);
    const fence = line.match(/^ {0,3}```([\w.+-]*)\s*$/);

    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (fence) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^ {0,3}```\s*$/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      const language = fence[1] && /^[\w.+-]+$/.test(fence[1]) ? `language-${fence[1]}` : undefined;
      blocks.push(<pre key={`code-${blocks.length}`}><code className={language}>{codeLines.join('\n')}</code></pre>);
      continue;
    }

    const heading = normalized.match(/^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const Heading = `h${heading[1].length}`;
      blocks.push(<Heading key={`heading-${blocks.length}`}>{renderInline(heading[2], `heading-${blocks.length}`)}</Heading>);
      index += 1;
      continue;
    }

    const listItem = normalized.match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      const ordered = /^\d/.test(listItem[1]);
      const items = [];
      while (index < lines.length) {
        const item = unescapeMarkdown(lines[index]).match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[1]) !== ordered) break;
        items.push(<li key={`item-${items.length}`}>{renderInline(item[2], `list-${blocks.length}-${items.length}`)}</li>);
        index += 1;
      }
      const List = ordered ? 'ol' : 'ul';
      blocks.push(<List key={`list-${blocks.length}`}>{items}</List>);
      continue;
    }

    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    if (!paragraph.length) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(
      <p key={`paragraph-${blocks.length}`}>
        {paragraph.map((part, partIndex) => (
          <React.Fragment key={`line-${partIndex}`}>
            {partIndex > 0 && <br />}
            {renderInline(part, `paragraph-${blocks.length}-${partIndex}`)}
          </React.Fragment>
        ))}
      </p>,
    );
  }

  return <div className="answer-text">{blocks}</div>;
}
