import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatWindow } from './chat-window';
import { ChatService, Message } from '../../services/chat.service';
import { AudioService } from '../../services/audio.service';
import { of } from 'rxjs';
import { By } from '@angular/platform-browser';
import { ChangeDetectorRef } from '@angular/core';
import { vi } from 'vitest';

describe('ChatWindow', () => {
  let component: ChatWindow;
  let fixture: ComponentFixture<ChatWindow>;
  let chatServiceSpy: any;
  let routerSpy: any;
  let audioServiceSpy: any;

  beforeEach(async () => {
    chatServiceSpy = {
      getHistory: vi.fn(),
      sendMessage: vi.fn(),
      notifyThreadCreated: vi.fn(),
      refreshThreads: vi.fn(),
      externalMessage$: of()
    };
    routerSpy = {
      navigate: vi.fn()
    };
    audioServiceSpy = {
      playBotReply: vi.fn(),
      playSendMessage: vi.fn(),
      playNewChat: vi.fn(),
      playChangeThread: vi.fn()
    };

    // Default mock returns
    chatServiceSpy.getHistory.mockReturnValue(of({ messages: [] }));

    await TestBed.configureTestingModule({
      imports: [ChatWindow],
      providers: [
        { provide: ChatService, useValue: chatServiceSpy },
        { provide: Router, useValue: routerSpy },
        { provide: AudioService, useValue: audioServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: (key: string) => null })
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ChatWindow);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load history when threadId is present', () => {
    // Re-configure for this specific test
    const threadId = 'thread-1';
    const mockMessages: Message[] = [{ type: 'ai', content: 'Hello' }];
    chatServiceSpy.getHistory.mockReturnValue(of({ messages: mockMessages }));

    // Manually trigger ngOnInit with new params or call loadHistory directly
    component.loadHistory(threadId);

    expect(chatServiceSpy.getHistory).toHaveBeenCalledWith(threadId);
    expect(component.messages).toEqual(mockMessages);
  });

  it('should send a message', () => {
    const message = 'Hello world';
    const response = { thread_id: 'thread-1', status: 'processing' };
    chatServiceSpy.sendMessage.mockReturnValue(of(response));
    const startPollingSpy = vi.spyOn(component, 'startPolling');

    component.threadId = 'thread-1';
    component.newMessage = message;
    component.sendMessage();

    expect(chatServiceSpy.sendMessage).toHaveBeenCalledWith(message, 'thread-1');
    expect(component.messages.length).toBe(1); // Human only
    expect(component.messages[0].content).toBe('Hello world');
    expect(startPollingSpy).toHaveBeenCalledWith('thread-1');
  });

  it('should navigate to new thread on first message', () => {
    const message = 'New Thread';
    const response = { thread_id: 'new-thread', status: 'processing' };
    chatServiceSpy.sendMessage.mockReturnValue(of(response));
    const startPollingSpy = vi.spyOn(component, 'startPolling');

    component.threadId = null;
    component.newMessage = message;
    component.sendMessage();

    expect(routerSpy.navigate).toHaveBeenCalledWith(['../chat', 'new-thread'], expect.anything());
    expect(startPollingSpy).toHaveBeenCalledWith('new-thread');
  });

  it('should conditionally render an image block if additional_kwargs.image_url is present', () => {
    const threadId = 'thread-image';
    const mockMessages: Message[] = [{
      type: 'ai',
      content: 'Here is your image:',
      additional_kwargs: { image_url: 'https://fake-image.com/pic.jpg' }
    }];

    chatServiceSpy.getHistory.mockReturnValue(of({ messages: mockMessages }));

    component.loadHistory(threadId);
    fixture.detectChanges();

    const imgElement = fixture.debugElement.query(By.css('.image-block img'));
    expect(imgElement).toBeTruthy();
    expect(imgElement.nativeElement.src).toBe('https://fake-image.com/pic.jpg');
  });

  it('should not show content text if mfe_contents has items', () => {
    const mockMessages: Message[] = [{
      type: 'ai',
      content: 'I am AI',
      additional_kwargs: {
        mfe_contents: [{ mfe: 'mfe1', component: './Comp', content: {} }]
      }
    }];
    chatServiceSpy.getHistory.mockReturnValue(of({ messages: mockMessages }));
    component.loadHistory('thread-1');
    fixture.detectChanges();

    const contentElement = fixture.debugElement.query(By.css('.markdown-body'));
    expect(contentElement).toBeNull();
  });

  it('should show content text if mfe_contents is empty', () => {
    const mockMessages: Message[] = [{
      type: 'ai',
      content: 'I am AI',
      additional_kwargs: {
        mfe_contents: []
      }
    }];
    chatServiceSpy.getHistory.mockReturnValue(of({ messages: mockMessages }));
    component.loadHistory('thread-1');
    fixture.detectChanges();

    const contentElement = fixture.debugElement.query(By.css('.markdown-body'));
    expect(contentElement).toBeTruthy();
  });

  describe('Scrolling', () => {
    it('should set element.scrollTop to scrollHeight when scrollToBottom(true) is called', () => {
      const scrollContainer = component['scrollContainer'].nativeElement;
      Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
      Object.defineProperty(scrollContainer, 'scrollTop', { value: 0, writable: true, configurable: true });

      component.scrollToBottom(true);
      expect(scrollContainer.scrollTop).toBe(1000);
      expect((component as any).userAtBottom).toBe(true);
    });

    it('should NOT set element.scrollTop to scrollHeight when scrollToBottom() is called and userAtBottom is false', () => {
      const scrollContainer = component['scrollContainer'].nativeElement;
      Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
      Object.defineProperty(scrollContainer, 'scrollTop', { value: 0, writable: true, configurable: true });

      (component as any).userAtBottom = false;
      component.scrollToBottom();
      expect(scrollContainer.scrollTop).toBe(0);
    });

    it('should set userAtBottom based on scroll position in onScroll', () => {
      const scrollContainer = component['scrollContainer'].nativeElement;
      Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
      Object.defineProperty(scrollContainer, 'clientHeight', { value: 500, configurable: true });
      Object.defineProperty(scrollContainer, 'scrollTop', { value: 550, writable: true, configurable: true }); // Near bottom (1000 - 550 - 500 = -50 < 50)

      component.onScroll();
      expect((component as any).userAtBottom).toBe(true);

      Object.defineProperty(scrollContainer, 'scrollTop', { value: 100, writable: true, configurable: true }); // Far from bottom (1000 - 100 - 500 = 400 > 50)
      component.onScroll();
      expect((component as any).userAtBottom).toBe(false);
    });
  });
});
