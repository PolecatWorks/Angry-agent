import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

export const devAuthInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  let newReq = req;

  // Add fake JWT for dev mode if Authorization header is missing
  if (!req.headers.has('Authorization')) {
    // Generate a simple base64 encoded JWT. We only need the payload for 'name' claim.
    const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }));
    const payload = btoa(JSON.stringify({ sub: 'default-user', name: 'Dev User' }));
    const fakeJwt = `${header}.${payload}.`;

    newReq = req.clone({
      headers: req.headers.set('Authorization', `Bearer ${fakeJwt}`)
    });
  }

  return next(newReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Catch authentication/authorization errors and route to the error page
      if (error.status === 401 || error.status === 403) {
        const errorMsg = error.error?.error || 'Authentication failed. Please check your credentials or access rights.';
        router.navigate(['/error'], { state: { error: errorMsg } });
      }
      return throwError(() => error);
    })
  );
};
