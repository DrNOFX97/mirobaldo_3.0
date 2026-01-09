;/*FB_PKG_DELIM*/

__d("getReferrerURI",["ErrorGuard","URI","isFacebookURI"],(function(a,b,c,d,e,f,g){"use strict";function b(){if(a.PageTransitions&&a.PageTransitions.isInitialized())return a.PageTransitions.getReferrerURI();else{var b=c("ErrorGuard").applyWithGuard(function(a){return c("URI").tryParseURI(a)},null,[document.referrer]);return b&&c("isFacebookURI")(b)?b:null}}g["default"]=b}),98);