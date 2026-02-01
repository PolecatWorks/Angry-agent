import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { vi } from 'vitest';
import { AuthService } from '../../services/auth.service';

import { MainLayout } from './main-layout';

describe('MainLayout', () => {
  let component: MainLayout;
  let fixture: ComponentFixture<MainLayout>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MainLayout],
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
        },
        provideHttpClient(),
        {
          provide: AuthService,
          useValue: {
            getUserId: () => 'test-user',
            isLoggedIn: () => true
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(MainLayout);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });



  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
