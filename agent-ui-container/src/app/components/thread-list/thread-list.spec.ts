import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Thread } from '../../services/chat.service';
import { ThreadList } from './thread-list';
import { of, Subject, BehaviorSubject } from 'rxjs';
import { vi } from 'vitest';
import { SharedContextService } from 'mfe-shared';

describe('ThreadList', () => {
  let component: ThreadList;
  let fixture: ComponentFixture<ThreadList>;
  let chatServiceSpy: any;
  let routerSpy: any;
  let routerEventsSpec: Subject<any>; // Declare routerEventsSpec here

  beforeEach(async () => {
    chatServiceSpy = {
      threads$: new BehaviorSubject([]),
      refreshThreads: vi.fn(),
      getThreads: vi.fn()
    };

    // Router events setup
    routerEventsSpec = new Subject<any>();
    routerSpy = {
      navigate: vi.fn(),
      events: routerEventsSpec.asObservable(),
      url: '/chat/1'
    };

    await TestBed.configureTestingModule({
      imports: [ThreadList],
      providers: [
        { provide: ChatService, useValue: chatServiceSpy },
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: (key: string) => null })
          }
        },
        {
          provide: SharedContextService,
          useValue: { context$: of({}) }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ThreadList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should refresh threads on init', () => {
    expect(chatServiceSpy.refreshThreads).toHaveBeenCalled();
  });

  it('should delete thread', () => {
    const threadId = '1';
    const event = { stopPropagation: vi.fn(), preventDefault: vi.fn() } as any;

    // Setup confirm mock
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    chatServiceSpy.deleteThread = vi.fn().mockReturnValue(of({}));

    component.deleteThread(event, threadId);

    expect(event.stopPropagation).toHaveBeenCalled();
    expect(chatServiceSpy.deleteThread).toHaveBeenCalledWith(threadId);
    expect(chatServiceSpy.refreshThreads).toHaveBeenCalled();

    confirmSpy.mockRestore();
  });
});
