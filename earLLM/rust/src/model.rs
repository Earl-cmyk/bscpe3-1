use std::collections::HashMap;
use std::fs;
use std::path::Path;
use serde::Deserialize;
use crate::vocabulary::Vocabulary;

#[derive(Debug, Deserialize)]
struct ArtifactJson {
    format_version: u32,
    model_type: String,
    embedding_dim: usize,
    hidden_dim: usize,
    vocab_size: usize,
    num_labels: usize,
    labels: Vec<String>,
    vocab: HashMap<String, u32>,
    #[serde(rename="E")] e: Vec<Vec<f32>>,
    #[serde(rename="W1")] w1: Vec<Vec<f32>>,
    #[serde(rename="b1")] b1: Vec<f32>,
    #[serde(rename="W2")] w2: Vec<Vec<f32>>,
    #[serde(rename="b2")] b2: Vec<f32>,
}

#[derive(Debug, thiserror::Error)]
pub enum ModelError {
    #[error("failed to read model artifact at {path}: {source}")]
    Io { path:String, #[source] source:std::io::Error },
    #[error("failed to parse model artifact JSON: {0}")]
    Parse(#[from] serde_json::Error),
    #[error("invalid model artifact: {0}")]
    Invalid(String),
}

pub struct Model {
    pub embedding_dim: usize,
    pub hidden_dim: usize,
    pub num_labels: usize,
    pub labels: Vec<String>,
    pub vocab: Vocabulary,
    embedding: Vec<Vec<f32>>, // [V,D]
    w1: Vec<Vec<f32>>,        // [D,H]
    b1: Vec<f32>,             // [H]
    w2: Vec<Vec<f32>>,        // [H,C]
    b2: Vec<f32>,             // [C]
}

impl Model {
    pub fn load<P:AsRef<Path>>(path:P)->Result<Self,ModelError>{
        let p=path.as_ref();
        let raw=fs::read_to_string(p).map_err(|e|ModelError::Io{path:p.display().to_string(),source:e})?;
        let a:ArtifactJson=serde_json::from_str(&raw)?;
        if a.format_version < 2 || a.model_type != "embedding_mlp_relu" { return Err(ModelError::Invalid(format!("expected format v2 embedding_mlp_relu, got v{} {}",a.format_version,a.model_type))); }
        if a.labels.is_empty() { return Err(ModelError::Invalid("model contains no labels".into())); }
        if a.e.len()!=a.vocab_size || a.w1.len()!=a.embedding_dim || a.w2.len()!=a.hidden_dim || a.b1.len()!=a.hidden_dim || a.b2.len()!=a.num_labels || a.labels.len()!=a.num_labels { return Err(ModelError::Invalid("tensor metadata dimensions do not agree".into())); }
        if a.e.iter().any(|r|r.len()!=a.embedding_dim) || a.w1.iter().any(|r|r.len()!=a.hidden_dim) || a.w2.iter().any(|r|r.len()!=a.num_labels) { return Err(ModelError::Invalid("tensor row dimensions do not agree with config".into())); }
        Ok(Self{embedding_dim:a.embedding_dim,hidden_dim:a.hidden_dim,num_labels:a.num_labels,labels:a.labels,vocab:Vocabulary::from_map(a.vocab),embedding:a.e,w1:a.w1,b1:a.b1,w2:a.w2,b2:a.b2})
    }

    #[allow(clippy::too_many_arguments)]
    pub fn from_parts(embedding_dim:usize,hidden_dim:usize,labels:Vec<String>,vocab:Vocabulary,embedding:Vec<Vec<f32>>,w1:Vec<Vec<f32>>,b1:Vec<f32>,w2:Vec<Vec<f32>>,b2:Vec<f32>)->Self{
        Self{embedding_dim,hidden_dim,num_labels:labels.len(),labels,vocab,embedding,w1,b1,w2,b2}
    }

    pub fn predict_probs(&self, token_ids:&[u32])->Vec<f32>{
        let mut pooled=vec![0.0f32;self.embedding_dim]; let mut count=0usize;
        for &id in token_ids { if id==crate::vocabulary::PAD_ID {continue;} if let Some(row)=self.embedding.get(id as usize){ for d in 0..self.embedding_dim {pooled[d]+=row[d];} count+=1; } }
        if count>0 { let n=count as f32; for x in &mut pooled {*x/=n;} }
        let mut hidden=vec![0.0f32;self.hidden_dim];
        for h in 0..self.hidden_dim { let mut x=self.b1[h]; for d in 0..self.embedding_dim {x+=pooled[d]*self.w1[d][h];} hidden[h]=x.max(0.0); }
        let mut logits=self.b2.clone();
        for h in 0..self.hidden_dim { for c in 0..self.num_labels {logits[c]+=hidden[h]*self.w2[h][c];} }
        softmax(&logits)
    }
}
fn softmax(logits:&[f32])->Vec<f32>{ let max=logits.iter().copied().fold(f32::NEG_INFINITY,f32::max); let mut e=Vec::with_capacity(logits.len()); for &x in logits {e.push((x-max).exp());} let sum:f32 = e.iter().sum(); e.into_iter().map(|x|x/sum).collect() }

#[cfg(test)]
mod tests{
 use super::*; use std::collections::HashMap;
 fn tiny()->Model{let mut v=HashMap::new();v.insert("[PAD]".into(),0);v.insert("[UNK]".into(),1);v.insert("add".into(),2);v.insert("deadline".into(),3);Model::from_parts(2,2,vec!["GET".into(),"CREATE_DEADLINE".into()],Vocabulary::from_map(v),vec![vec![0.,0.],vec![0.,0.],vec![1.,0.],vec![0.,1.]],vec![vec![0.,0.],vec![0.,0.]],vec![0.,0.],vec![vec![0.,0.],vec![0.,5.]],vec![0.,0.])}
 #[test] fn probabilities_sum(){let m=tiny();let p=m.predict_probs(&[2,3]);assert!((p.iter().sum::<f32>()-1.).abs()<1e-5);}
 #[test] fn shape(){let m=tiny();assert_eq!(m.predict_probs(&[2,3]).len(),2);}
}
