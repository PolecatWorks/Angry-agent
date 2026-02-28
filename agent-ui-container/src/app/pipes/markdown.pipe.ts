import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

@Pipe({
  name: 'markdown',
  standalone: true
})
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: string | undefined): SafeHtml {
    if (!value) {
      return '';
    }

    // Parse the markdown
    const html = marked.parse(value) as string;

    // Sanitize the HTML
    const cleanHtml = DOMPurify.sanitize(html);

    // Tell Angular to trust this HTML
    return this.sanitizer.bypassSecurityTrustHtml(cleanHtml);
  }
}
