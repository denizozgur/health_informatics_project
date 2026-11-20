"""PSQ exploratory data analysis used for the LEMON project.

Produces descriptive statistics, box plots, histograms, an ECDF and Pearson/
Spearman correlations. Does not perform hypothesis tests or clinical classification.
Joy is retained in its original direction. Outlying scores are not removed.
The output analysis.json includes participant IDs: do not publish it inadvertently.
"""
import os
os.environ.setdefault('MPLCONFIGDIR', str(__import__('tempfile').gettempdir() + '/psq-eda-mpl'))
import csv,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# Configure input/output paths from Terminal or the notebook.
import argparse
parser = argparse.ArgumentParser(description="PSQ descriptive EDA and correlations")
parser.add_argument("--input", type=Path, required=True, help="Path to PSQ.csv")
parser.add_argument("--output", type=Path, default=Path("psq_results"))
args = parser.parse_args()
S = args.input.expanduser().resolve()
O = args.output.expanduser().resolve()
O.mkdir(parents=True, exist_ok=True)
(O / "figures").mkdir(exist_ok=True)

# Use named columns so an unrelated or reordered CSV cannot silently change scoring.
with S.open(encoding="utf-8-sig", newline="") as source:
 rows = list(csv.DictReader(source))
if not rows:
 raise ValueError("The input CSV has no data rows.")
cols = ["PSQ_Worries", "PSQ_Tension", "PSQ_Joy", "PSQ_Demands", "PSQ_OverallScore"]
if not {"ID", *cols}.issubset(rows[0]):
 raise ValueError("Expected columns: ID and " + ", ".join(cols))
def parse(v):
 try:return float(v)
 except (ValueError, TypeError):return np.nan
A=np.array([[parse(r[c]) for c in cols] for r in rows]);valid=np.isfinite(A)
assert len(set(r['ID'] for r in rows))==len(rows)
assert not ((A[valid]<0)|(A[valid]>100)).any()
complete=valid.all(1)
if not complete.any():
 raise ValueError("There are no complete records.")
formula=(A[:,0]+A[:,1]+100-A[:,2]+A[:,3])/4
err=float(np.nanmax(abs(formula-A[:,4])))
labels=['Worries','Tension','Joy','Demands','Total score'];colors=['#507A94','#507A94','#A17A44','#507A94','#294F67']
stats=[]
# Descriptive statistics use each score's available observations; correlations below use complete cases.
for i,c in enumerate(cols):
 x=A[valid[:,i],i];q1,med,q3=np.quantile(x,[.25,.5,.75]);iqr=q3-q1
 stats.append(dict(Measure=labels[i],N=len(x),Missing=int((~valid[:,i]).sum()),Mean=float(x.mean()),SD=float(x.std(ddof=1)),Q1=float(q1),Median=float(med),Q3=float(q3),IQR=float(iqr),Min=float(x.min()),Max=float(x.max()),Outside_1p5_IQR=int(((x<q1-1.5*iqr)|(x>q3+1.5*iqr)).sum())))
with (O/'PSQ_summary_statistics.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
payload=dict(source=str(S),sha256=hashlib.sha256(S.read_bytes()).hexdigest(),source_n=len(rows),complete_n=int(complete.sum()),missing_n=int((~complete).sum()),quartiles='Linear interpolation, equivalent to Excel QUARTILE.INC',overall_formula_max_absolute_error=err,statistics=stats,raw_rows=[[r['ID']]+[None if not np.isfinite(v) else float(v) for v in a] for r,a in zip(rows,A)],columns=['ID', *cols])
(O/'analysis.json').write_text(json.dumps(payload,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
rng=np.random.default_rng(413)
fig,ax=plt.subplots(figsize=(10,5.3),layout='constrained')
groups=[A[valid[:,i],i] for i in range(5)]
bp=ax.boxplot(groups,patch_artist=True,widths=.48,showfliers=False,medianprops={'color':'black','linewidth':2})
for i,(x,col,b) in enumerate(zip(groups,colors,bp['boxes']),1):
 b.set(facecolor=col,alpha=.25);ax.scatter(i+rng.uniform(-.16,.16,len(x)),x,s=12,color=col,alpha=.32,zorder=3,edgecolors='none')
ax.set(xticks=range(1,6),xticklabels=labels,ylim=(-3,104),ylabel='PSQ score (0–100)',title=f'PSQ distributions: box plots with individual observations (n={int(complete.sum())})')
ax.grid(axis='y',alpha=.15);fig.savefig(O/'figures/01_PSQ_boxplots.png',dpi=250);plt.close(fig)
fig,axes=plt.subplots(2,3,figsize=(11,6.4),layout='constrained')
for i,ax in enumerate(axes.flat[:5]):
 x=groups[i];st=stats[i];ax.hist(x,bins=np.arange(0,101,10),color=colors[i],edgecolor='white',linewidth=.8)
 ax.axvspan(st['Q1'],st['Q3'],alpha=.12,color='#D39531',label='Q1–Q3')
 ax.axvline(st['Median'],color='#252525',ls='--',lw=1.5,label='Median');ax.set(xlim=(0,100),xlabel='Score (0–100)',ylabel='Participants',title=f"{labels[i]} (n={len(x)})")
 ax.text(.97,.95,f"Median {st['Median']:.2f}\nIQR {st['IQR']:.2f}",ha='right',va='top',transform=ax.transAxes,fontsize=9)
axes.flat[0].legend(fontsize=8,frameon=False,loc='upper left')
axes.flat[5].axis('off');axes.flat[5].text(.04,.85,f'Scope and interpretation\n\n{int(complete.sum())} complete / {len(rows)} participants\nMissing values kept empty\nNo imputation or exclusions of high scores\nJoy is plotted as supplied.\nHigher Joy is not higher stress.\n\nShading: middle 50% (Q1–Q3)\nDashed line: median',va='top',fontsize=10,linespacing=1.6)
fig.suptitle('PSQ score distributions and interquartile ranges',fontsize=14);fig.savefig(O/'figures/02_PSQ_distributions.png',dpi=250);plt.close(fig)
fig,ax=plt.subplots(figsize=(8.8,4.5),layout='constrained');x=np.sort(groups[-1]);st=stats[-1]
ax.step(x,np.arange(1,len(x)+1)/len(x),where='post',color=colors[-1],lw=2)
ax.axvspan(st['Q1'],st['Q3'],color='#D39531',alpha=.15);ax.axhline(.5,color='gray',ls=':',lw=1)
ax.axvline(st['Median'],color='black',ls='--',lw=1,label=f"Median = {st['Median']:.2f}")
ax.set(xlim=(0,100),ylim=(0,1.03),xlabel='PSQ total score (0–100)',ylabel='Cumulative proportion',title=f'PSQ total score: empirical cumulative distribution (n={len(groups[-1])})')
ax.text(.58,.3,f"Middle 50%: {st['Q1']:.2f}–{st['Q3']:.2f}\nIQR: {st['IQR']:.2f}\nMean: {st['Mean']:.2f}\nObserved range: {st['Min']:.2f}–{st['Max']:.2f}",transform=ax.transAxes,linespacing=1.7);ax.legend(frameon=False);ax.grid(alpha=.12);fig.savefig(O/'figures/03_PSQ_total_ECDF.png',dpi=250);plt.close(fig)
print(json.dumps({k:v for k,v in payload.items() if k not in ['raw_rows','columns','source','sha256']},indent=2))


# Correlation analysis and heatmaps
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# Correlations use only participants with all five scores present.
d=json.loads((O/'analysis.json').read_text())
a=np.array([[np.nan if v is None else v for v in row[1:]] for row in d['raw_rows']],dtype=float)
a=a[np.isfinite(a).all(1)]
if len(a) < 2 or np.any(np.std(a, axis=0) == 0):
 raise ValueError("Correlations need at least two complete records and nonconstant scores.")
labels=[x['Measure'] for x in d['statistics']];p=np.corrcoef(a,rowvar=False);s=spearmanr(a,axis=0).statistic
for kind,m in [('pearson',p),('spearman',s)]:
 with (O/f'PSQ_{kind}_correlations.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['Measure',*labels]);w.writerows([[label,*map(float,row)] for label,row in zip(labels,m)])
(O/'correlations.json').write_text(json.dumps(dict(n=len(a),labels=labels,pearson=p.tolist(),spearman=s.tolist(),missing_policy='Complete cases across all five scores; incomplete participants excluded; no imputation',inference='Descriptive effect sizes only; no significance tests',total_note='Total is derived from subscales, so its correlations are mathematically coupled. Joy retained as supplied.'),indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
for ax,m,title in zip(axes,[p,s],['Pearson r: linear association','Spearman rho: rank association']):
 im=ax.imshow(m,cmap='RdBu_r',vmin=-1,vmax=1)
 ax.set_xticks(range(5),labels,rotation=35,ha='right');ax.set_yticks(range(5),labels);ax.set_title(title,pad=12)
 for i in range(5):
  for j in range(5):ax.text(j,i,f'{m[i,j]:.2f}',ha='center',va='center',color='white' if abs(m[i,j])>.65 else '#17212A',fontsize=12)
 ax.spines[:].set_visible(False)
fig.colorbar(im,ax=axes,shrink=.8,label='Correlation coefficient',ticks=[-1,-.5,0,.5,1]);fig.suptitle(f'PSQ correlations ({len(a)} complete participants)',fontsize=15)
fig.savefig(O/'figures/04_PSQ_correlations.png',dpi=250);plt.close(fig)
for i in range(4):print(labels[i], 'total Pearson',round(p[i,4],4),'Spearman',round(s[i,4],4))
