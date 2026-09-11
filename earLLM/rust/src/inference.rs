use serde::Serialize;
use crate::classifier::{argmax_label,band_for,ConfidenceBand};
use crate::entities::{extract_entities,Entities};
use crate::model::Model;
use crate::tokenizer::word_tokenize;

#[derive(Debug,Serialize)]
pub struct StructuredPrediction{pub intent:String,pub confidence:f32,pub confidence_band:ConfidenceBand,pub entities:Entities}

pub fn predict(model:&Model,text:&str)->StructuredPrediction{
    let tokens=word_tokenize(text); let ids=model.vocab.encode_tokens(&tokens); let known=ids.iter().filter(|&&x|x!=crate::vocabulary::UNK_ID && x!=crate::vocabulary::PAD_ID).count();
    let probs=model.predict_probs(&ids); let (mut intent,confidence)=argmax_label(&model.labels,&probs);
    if text.trim().is_empty() || known==0 || confidence < 0.35 { intent="UNKNOWN".to_string(); }
    let band=if intent=="UNKNOWN"{ConfidenceBand::ClarificationRequired}else{band_for(confidence)};
    let entities=extract_entities(text,&intent);
    StructuredPrediction{intent,confidence,confidence_band:band,entities}
}

#[cfg(test)]
mod tests{use super::*;use crate::model::Model;use crate::vocabulary::Vocabulary;use std::collections::HashMap;
fn tiny()->Model{let mut v=HashMap::new();v.insert("[PAD]".into(),0);v.insert("[UNK]".into(),1);v.insert("add".into(),2);v.insert("hdl".into(),3);v.insert("deadline".into(),4);Model::from_parts(2,2,vec!["OTHER".into(),"CREATE_DEADLINE".into()],Vocabulary::from_map(v),vec![vec![0.0,0.0],vec![0.0,0.0],vec![0.1,0.0],vec![0.1,0.0],vec![0.0,1.0]],vec![vec![0.0,0.0],vec![0.0,0.0]],vec![0.0,0.0],vec![vec![0.0,0.0],vec![0.0,0.0]],vec![0.0,1.0])}
#[test]fn predicts(){let r=predict(&tiny(),"add HDL deadline tomorrow");assert_eq!(r.intent,"CREATE_DEADLINE");assert!(r.entities.contains_key("course"));}
#[test]fn unknown_is_safe(){let r=predict(&tiny(),"zzzz qqqq");assert_eq!(r.intent,"UNKNOWN");}
}
