'use strict';
const VP={
 units:{Pa:1,kPa:1000,mbar:100,hPa:100,bar:100000,atm:101325,mmHg:101325/760,Torr:101325/760,psi:6894.757293168},
 pressure(s,T){if(!Number.isFinite(T)||T<=0)throw Error('Température absolue invalide.');if(T<s.Tmin-1e-8||T>s.Tmax+1e-8)throw Error('Hors de la plage publiée : calcul bloqué.');let l;if(s.model==='Antoine'){if(T+s.C<=0)throw Error('Singularité Antoine.');l=Math.LN10*(s.A-s.B/(T+s.C));}else l=s.C1+s.C2/T+s.C3*Math.log(T)+s.C4*T**s.C5;let p=Math.exp(l);if(!Number.isFinite(p)||p<=0)throw Error('Pression non calculable.');return p;},
 temperature(s,p){if(!Number.isFinite(p)||p<=0)throw Error('La pression absolue doit être positive.');const loP=this.pressure(s,s.Tmin),hiP=this.pressure(s,s.Tmax);if(p<loP||p>hiP)throw Error('Pression hors de la plage publiée : calcul bloqué.');let lo=s.Tmin,hi=s.Tmax;for(let i=0;i<90;i++){let m=(lo+hi)/2;if(this.pressure(s,m)<p)lo=m;else hi=m;}return(lo+hi)/2;},
 calibrate(t1,p1,t2,p2){if(![t1,p1,t2,p2].every(Number.isFinite)||Math.min(t1,p1,t2,p2)<=0||Math.abs(t1-t2)<1e-8)throw Error('Deux points distincts, T en K et P positives, sont requis.');let h=8.31446261815324*Math.log(p2/p1)/(1/t1-1/t2);if(!Number.isFinite(h)||h<=0)throw Error('La pression doit augmenter avec la température.');return h;},
 cc(t1,p1,h,x,inverse){if(![t1,p1,h,x].every(Number.isFinite)||Math.min(t1,p1,h,x)<=0)throw Error('Valeurs positives requises, températures en K.');let y=inverse?1/(1/t1-8.31446261815324/h*Math.log(x/p1)):p1*Math.exp(h/8.31446261815324*(1/t1-1/x));if(!Number.isFinite(y)||y<=0)throw Error('Estimation physiquement invalide.');return y;}
};
if(typeof module!=='undefined')module.exports=VP;
