import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { vi } from 'vitest';
import { ChatWindow } from './chat-window';


describe('ChatWindow', () => {
  let component: ChatWindow;
  let fixture: ComponentFixture<ChatWindow>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatWindow],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: {
              subscribe: (fn: (value: any) => void) => {
                fn({
                  get: (key: string) => null
                });
              }
            }
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ChatWindow);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { });
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
